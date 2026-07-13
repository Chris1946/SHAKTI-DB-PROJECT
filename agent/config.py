"""
PulseTrace Agent — Configuration

Loads agent configuration from environment variables.
Uses python-dotenv for .env file support.

Configuration hierarchy:
  1. Environment variables (highest priority)
  2. .env file in agent directory
  3. Defaults defined here (lowest priority)
"""

from __future__ import annotations

import os
import platform
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    # Look for .env in parent directory (project root)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try local .env
        load_dotenv()
except ImportError:
    pass


def _get_hostname() -> str:
    """Get the machine hostname, with override support."""
    override = os.getenv("AGENT_HOSTNAME", "").strip()
    if override:
        return override
    return socket.gethostname()


@dataclass
class AgentConfig:
    """Agent configuration loaded from environment."""

    # Backend connection
    backend_url: str = os.getenv("AGENT_BACKEND_URL", "http://localhost:8000")
    api_key: str = os.getenv("AGENT_API_KEY", "")

    # Collection
    collection_interval: int = int(os.getenv("COLLECTION_INTERVAL", "5"))
    top_processes: int = int(os.getenv("TOP_PROCESSES", "10"))
    hostname: str = field(default_factory=_get_hostname)

    # HTTP
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Agent identity
    agent_version: str = "0.1.0"
    os_name: str = platform.system()
    os_version: str = platform.release()
    kernel_version: str = platform.version()

    # Enabled collectors
    enabled_collectors: List[str] = field(
        default_factory=lambda: ["cpu", "memory", "disk", "network", "process"]
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.collection_interval < 1:
            raise ValueError("COLLECTION_INTERVAL must be >= 1 second")
        if self.top_processes < 1:
            raise ValueError("TOP_PROCESSES must be >= 1")

    def summary(self) -> str:
        """Return a human-readable configuration summary."""
        return (
            f"Agent Configuration:\n"
            f"  Backend URL:    {self.backend_url}\n"
            f"  API Key:        {'SET' if self.api_key else 'NOT SET'}\n"
            f"  Hostname:       {self.hostname}\n"
            f"  Interval:       {self.collection_interval}s\n"
            f"  Top Processes:  {self.top_processes}\n"
            f"  Collectors:     {', '.join(self.enabled_collectors)}\n"
            f"  OS:             {self.os_name} {self.os_version}\n"
            f"  Agent Version:  {self.agent_version}"
        )


# Singleton configuration
config = AgentConfig()
