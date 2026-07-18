"""
PulseTrace Agent — Memory Collector

Collects:
  • Total, used, available RAM and usage percentage
  • Total, used swap and usage percentage

These are the primary indicators for memory pressure
and potential OOM situations.
"""

from __future__ import annotations

from typing import Any, Dict

import psutil

from collectors.base import BaseCollector


class MemoryCollector(BaseCollector):
    """Collects RAM and swap utilization metrics."""

    def __init__(self) -> None:
        super().__init__("memory")

    def _collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # Virtual memory (RAM)
        vm = psutil.virtual_memory()
        data["memory_total"] = vm.total
        # On macOS, vm.used excludes compressed memory and cached files,
        # which makes it much lower than what Activity Monitor reports.
        # Using (total - available) gives the true "in-use" memory that
        # matches Activity Monitor's "Memory Used" figure.
        data["memory_used"] = vm.total - vm.available
        data["memory_available"] = vm.available
        data["memory_percent"] = vm.percent

        # Swap
        swap = psutil.swap_memory()
        data["swap_total"] = swap.total
        data["swap_used"] = swap.used
        data["swap_percent"] = swap.percent

        return data
