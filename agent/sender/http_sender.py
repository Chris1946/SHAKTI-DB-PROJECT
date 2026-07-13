"""
PulseTrace Agent — HTTP Sender

Async HTTP client that sends collected metrics to the FastAPI
backend. Features:
  • Retry logic with exponential backoff
  • API key authentication
  • Connection health monitoring
  • Timeout configuration
  • Graceful error handling (never crashes the agent)

The sender is designed to survive backend restarts — it will
keep retrying until the backend comes back online.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("pulsetrace.sender")


class HTTPSender:
    """Sends metric batches to the PulseTrace backend."""

    def __init__(
        self,
        backend_url: str,
        api_key: str = "",
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._consecutive_failures = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            self._client = httpx.AsyncClient(
                base_url=self.backend_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def send_metrics(self, batch: Dict[str, Any]) -> bool:
        """Send a metrics batch to the backend.

        Implements retry with exponential backoff. Returns True
        on success, False on failure.

        Args:
            batch: Dictionary matching the MetricsBatch schema.

        Returns:
            True if metrics were accepted, False otherwise.
        """
        import asyncio

        client = await self._get_client()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.post("/api/v1/metrics", json=batch)

                if response.status_code == 201:
                    self._consecutive_failures = 0
                    data = response.json()
                    logger.info(
                        "Metrics sent successfully: system_id=%s, alerts=%s",
                        data.get("system_metric_id"),
                        data.get("alerts_generated"),
                    )
                    return True

                if response.status_code == 401:
                    logger.error(
                        "Authentication failed — check AGENT_API_KEY configuration"
                    )
                    return False

                logger.warning(
                    "Backend returned %d on attempt %d/%d: %s",
                    response.status_code,
                    attempt,
                    self.max_retries,
                    response.text[:200],
                )

            except httpx.ConnectError:
                logger.warning(
                    "Cannot connect to backend at %s (attempt %d/%d)",
                    self.backend_url,
                    attempt,
                    self.max_retries,
                )
            except httpx.TimeoutException:
                logger.warning(
                    "Request timed out (attempt %d/%d)", attempt, self.max_retries
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error sending metrics (attempt %d/%d): %s",
                    attempt,
                    self.max_retries,
                    exc,
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries:
                wait = 2 ** (attempt - 1)
                logger.debug("Retrying in %ds...", wait)
                await asyncio.sleep(wait)

        self._consecutive_failures += 1
        if self._consecutive_failures % 10 == 0:
            logger.error(
                "Backend unreachable for %d consecutive collection cycles",
                self._consecutive_failures,
            )

        return False

    async def health_check(self) -> bool:
        """Check if the backend is reachable.

        Returns:
            True if health endpoint responds, False otherwise.
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("HTTP client closed")
