"""
PulseTrace Agent — Process Collector

Collects the top N processes by CPU and memory usage. This data
powers root cause analysis — when CPU spikes, the dashboard
can show exactly which processes are responsible.

Platform notes:
  • AccessDenied is common for system processes — handled gracefully
  • cmdline() may be empty for kernel threads
  • On macOS, some process attributes require root access
"""

from __future__ import annotations

from typing import Any, Dict, List

import psutil

from collectors.base import BaseCollector


class ProcessCollector(BaseCollector):
    """Collects top N processes by resource usage."""

    def __init__(self, top_n: int = 10) -> None:
        super().__init__("process")
        self.top_n = top_n

    def _collect(self) -> Dict[str, Any]:
        """Collect top N processes by CPU usage.

        Returns:
            Dictionary with 'processes' key containing a list
            of process info dicts.
        """
        processes = self._get_top_processes()
        return {"processes": processes}

    def _get_top_processes(self) -> List[Dict[str, Any]]:
        """Get top N processes sorted by CPU usage.

        Uses psutil.process_iter with attrs for efficient bulk
        collection (avoids per-process system calls).
        """
        proc_list: List[Dict[str, Any]] = []

        for proc in psutil.process_iter(
            attrs=[
                "pid",
                "name",
                "username",
                "status",
                "cpu_percent",
                "memory_percent",
                "memory_info",
                "num_threads",
            ]
        ):
            try:
                info = proc.info
                if info is None:
                    continue

                # Skip zombie or dead processes
                if info.get("status") in ("zombie", "dead"):
                    continue

                # Some OS processes might return None for CPU/Memory, handle safely
                cpu_pct = info.get("cpu_percent") or 0.0
                mem_pct = info.get("memory_percent") or 0.0

                proc_data = {
                    "pid": info["pid"],
                    "name": info.get("name", "unknown"),
                    "username": info.get("username"),
                    "status": info.get("status"),
                    "cpu_percent": round(cpu_pct, 2),
                    "memory_percent": round(mem_pct, 2),
                    "memory_rss": (
                        info["memory_info"].rss
                        if info.get("memory_info")
                        else None
                    ),
                    "num_threads": info.get("num_threads"),
                    "command": self._get_cmdline(proc),
                }
                proc_list.append(proc_data)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU usage descending, take top N
        proc_list.sort(key=lambda p: p.get("cpu_percent", 0.0), reverse=True)
        return proc_list[: self.top_n]

    @staticmethod
    def _get_cmdline(proc: psutil.Process) -> str | None:
        """Safely retrieve a process command line."""
        try:
            cmdline = proc.cmdline()
            return " ".join(cmdline) if cmdline else None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
