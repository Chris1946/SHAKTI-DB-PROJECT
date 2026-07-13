"""
PulseTrace Agent — CPU Collector

Collects:
  • Overall CPU utilization percentage
  • Per-core CPU utilization
  • CPU frequency (if available)
  • Load averages (1, 5, 15 minute)

Platform notes:
  • Load averages use os.getloadavg() (Linux/macOS only)
  • CPU frequency may not be available in VMs or containers
"""

from __future__ import annotations

import os
from typing import Any, Dict

import psutil

from collectors.base import BaseCollector


class CPUCollector(BaseCollector):
    """Collects CPU utilization and load metrics."""

    def __init__(self) -> None:
        super().__init__("cpu")

    def _collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # Overall CPU percentage (non-blocking, interval=None uses
        # delta since last call)
        data["cpu_percent"] = psutil.cpu_percent(interval=None)

        # Per-core percentages
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        data["cpu_per_core"] = {
            f"core_{i}": pct for i, pct in enumerate(per_core)
        }

        # CPU frequency
        freq = self.safe_get(psutil.cpu_freq)
        if freq:
            data["cpu_freq_mhz"] = round(freq.current, 2)

        # Load averages (Unix only)
        try:
            load1, load5, load15 = os.getloadavg()
            data["load_avg_1"] = round(load1, 2)
            data["load_avg_5"] = round(load5, 2)
            data["load_avg_15"] = round(load15, 2)
        except (OSError, AttributeError):
            # Windows doesn't support getloadavg
            self.logger.debug("Load averages not available on this platform")

        return data
