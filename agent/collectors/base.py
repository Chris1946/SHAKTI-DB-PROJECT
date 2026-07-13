"""
PulseTrace Agent — Base Collector

Abstract base class for all metric collectors. Provides:
  • A consistent interface via collect()
  • Platform detection (Linux vs macOS vs other)
  • Safe collection wrapper with error handling
  • Logging integration

All concrete collectors (cpu, memory, disk, network, process)
inherit from this class.
"""

from __future__ import annotations

import logging
import platform
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for metric collectors.

    Subclasses must implement _collect() to gather metrics.
    The public collect() method wraps _collect() with error
    handling and logging.
    """

    # Class-level platform detection (computed once)
    PLATFORM = platform.system().lower()
    IS_LINUX = PLATFORM == "linux"
    IS_MACOS = PLATFORM == "darwin"

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"pulsetrace.collector.{name}")

    def collect(self) -> Dict[str, Any]:
        """Collect metrics with error handling.

        Returns:
            Dictionary of metric key-value pairs.
            Returns empty dict on failure (never crashes the agent).
        """
        try:
            data = self._collect()
            self.logger.debug("Collected %d metrics from %s", len(data), self.name)
            return data
        except Exception as exc:
            self.logger.error(
                "Failed to collect %s metrics: %s", self.name, exc, exc_info=True
            )
            return {}

    @abstractmethod
    def _collect(self) -> Dict[str, Any]:
        """Gather metrics from the system.

        Must be implemented by subclasses. Should return a flat
        dictionary of metric names to values.

        Raises:
            Any exception — caught by collect() wrapper.
        """
        ...

    @staticmethod
    def safe_get(func, default=None):
        """Safely call a function, returning default on failure.

        Useful for psutil calls that may raise AccessDenied or
        NotImplementedError on certain platforms.
        """
        try:
            return func()
        except (PermissionError, NotImplementedError, OSError, AttributeError):
            return default
