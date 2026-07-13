"""
PulseTrace Agent — Disk Collector

Collects:
  • Disk usage (total, used, free, percentage) for root partition
  • Disk I/O counters (cumulative read/write bytes)

The root partition is used as the primary indicator. On Linux
this is '/', on macOS it's also '/'.

I/O counters are cumulative — the dashboard calculates rates
by computing deltas between successive readings.
"""

from __future__ import annotations

from typing import Any, Dict

import psutil

from collectors.base import BaseCollector


class DiskCollector(BaseCollector):
    """Collects disk usage and I/O metrics."""

    def __init__(self, path: str = "/") -> None:
        super().__init__("disk")
        self.path = path

    def _collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # Disk usage for target partition
        try:
            usage = psutil.disk_usage(self.path)
            data["disk_total"] = usage.total
            data["disk_used"] = usage.used
            data["disk_free"] = usage.free
            data["disk_percent"] = usage.percent
        except OSError as exc:
            self.logger.warning("Failed to get disk usage for %s: %s", self.path, exc)

        # Disk I/O counters (cumulative)
        io = self.safe_get(psutil.disk_io_counters)
        if io:
            data["disk_read_bytes"] = io.read_bytes
            data["disk_write_bytes"] = io.write_bytes

        return data
