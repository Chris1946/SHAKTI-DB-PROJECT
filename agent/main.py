"""
PulseTrace Agent — Main Entry Point

The agent runs as a long-lived process that:
  1. Initializes metric collectors
  2. Runs a collection loop on a configurable interval
  3. Assembles collected metrics into a batch
  4. Sends the batch to the FastAPI backend
  5. Handles graceful shutdown on SIGINT/SIGTERM

Start with:
    python main.py

Or as a module:
    python -m main
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, List

import psutil

from config import config
from collectors.cpu import CPUCollector
from collectors.memory import MemoryCollector
from collectors.disk import DiskCollector
from collectors.network import NetworkCollector
from collectors.process import ProcessCollector
from collectors.thermal import ThermalCollector
from collectors.discovery import collect_system_profile

# Try to load eBPF collectors; gracefully degrade if unavailable
EBPF_AVAILABLE = False
try:
    from collectors.ebpf import EBPFDiskCollector, EBPFNetworkCollector
    EBPF_AVAILABLE = True
except ImportError as e:
    # This will happen on macOS or Linux without BCC installed
    pass
from sender.http_sender import HTTPSender

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("pulsetrace.agent")


# ============================================================
# Collector Registry
# ============================================================

COLLECTOR_MAP = {
    "cpu": CPUCollector,
    "memory": MemoryCollector,
    "disk": EBPFDiskCollector if EBPF_AVAILABLE else DiskCollector,
    "network": EBPFNetworkCollector if EBPF_AVAILABLE else NetworkCollector,
    "thermal": ThermalCollector,
    "process": lambda: ProcessCollector(top_n=config.top_processes),
}


class PulseTraceAgent:
    """Main agent that orchestrates collection and sending."""

    def __init__(self) -> None:
        self.config = config
        self.sender = HTTPSender(
            backend_url=config.backend_url,
            api_key=config.api_key,
            timeout=config.request_timeout,
            max_retries=config.max_retries,
        )
        self.collectors = self._init_collectors()
        self._running = False

    def _init_collectors(self) -> Dict:
        """Initialize enabled collectors."""
        collectors = {}
        for name in self.config.enabled_collectors:
            factory = COLLECTOR_MAP.get(name)
            if factory:
                collectors[name] = factory()
                logger.info("Initialized collector: %s", name)
            else:
                logger.warning("Unknown collector: %s (skipping)", name)
        return collectors

    def collect_all(self) -> Dict:
        """Run all collectors and merge results.

        Returns a flat dictionary of all metrics.
        """
        merged = {}
        for name, collector in self.collectors.items():
            data = collector.collect()
            merged.update(data)
        return merged

    def build_batch(self, metrics: Dict) -> Dict:
        """Build a MetricsBatch payload from raw metrics.

        Separates system metrics from process metrics and
        structures them for the backend API.
        """
        now = datetime.now(timezone.utc).isoformat()

        # System metrics (everything except processes)
        system = {
            "hostname": self.config.hostname,
            "collected_at": now,
        }

        # Map collected values to schema fields
        system_fields = [
            "cpu_percent", "cpu_per_core", "cpu_freq_mhz",
            "load_avg_1", "load_avg_5", "load_avg_15",
            "memory_total", "memory_used", "memory_available", "memory_percent",
            "swap_total", "swap_used", "swap_percent",
            "disk_total", "disk_used", "disk_free", "disk_percent",
            "disk_read_bytes", "disk_write_bytes",
            "net_bytes_sent", "net_bytes_recv",
            "net_packets_sent", "net_packets_recv",
            "net_errin", "net_errout", "net_dropin", "net_dropout",
            "cpu_temp_current", "cpu_temp_high", "cpu_temp_critical", "cpu_throttled",
        ]

        for field in system_fields:
            if field in metrics:
                system[field] = metrics[field]

        # Process metrics
        processes: List[Dict] = []
        raw_processes = metrics.get("processes", [])
        for proc in raw_processes:
            processes.append({
                "hostname": self.config.hostname,
                "collected_at": now,
                **proc,
            })

        return {
            "system": system,
            "processes": processes,
        }

    async def run(self) -> None:
        """Main collection loop.

        Runs until stopped via SIGINT/SIGTERM or _running is set to False.
        """
        self._running = True

        logger.info("=" * 60)
        logger.info("PulseTrace Agent v%s starting", self.config.agent_version)
        if EBPF_AVAILABLE:
            logger.info("Running in eBPF HIGH-PERFORMANCE mode")
        else:
            logger.info("Running in psutil FALLBACK mode (eBPF unavailable/macOS)")
        logger.info(self.config.summary())
        logger.info("=" * 60)

        # Prime CPU percent (first call always returns 0)
        psutil.cpu_percent(interval=None)

        # Check backend connectivity
        if await self.sender.health_check():
            logger.info("Backend connection verified: %s", self.config.backend_url)
            # Send system profile
            profile = collect_system_profile()
            await self.sender.send_profile(profile)
        else:
            logger.warning(
                "Backend not reachable at %s — will retry on each collection cycle",
                self.config.backend_url,
            )

        cycle = 0
        while self._running:
            cycle += 1
            try:
                # Collect
                metrics = self.collect_all()
                batch = self.build_batch(metrics)

                logger.debug(
                    "Cycle %d: CPU=%.1f%%, MEM=%.1f%%, DISK=%.1f%%",
                    cycle,
                    metrics.get("cpu_percent", 0),
                    metrics.get("memory_percent", 0),
                    metrics.get("disk_percent", 0),
                )

                # Send
                await self.sender.send_metrics(batch)

            except Exception as exc:
                logger.error("Collection cycle %d failed: %s", cycle, exc, exc_info=True)

            # Wait for next interval
            try:
                await asyncio.sleep(self.config.collection_interval)
            except asyncio.CancelledError:
                break

        logger.info("Agent stopped after %d collection cycles", cycle)

    async def stop(self) -> None:
        """Gracefully stop the agent."""
        logger.info("Stopping agent...")
        self._running = False
        await self.sender.close()


# ============================================================
# Entry Point
# ============================================================


async def main() -> None:
    """Entry point for the PulseTrace agent."""
    agent = PulseTraceAgent()

    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(agent.stop()))

    try:
        await agent.run()
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
