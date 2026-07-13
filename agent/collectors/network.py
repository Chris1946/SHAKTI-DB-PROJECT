"""
PulseTrace Agent — Network Collector

Collects:
  • Bytes sent/received (cumulative)
  • Packets sent/received (cumulative)
  • Error and drop counts

All counters are cumulative since system boot. The backend
and dashboard compute rates from successive readings.
"""

from __future__ import annotations

from typing import Any, Dict

import psutil

from collectors.base import BaseCollector


class NetworkCollector(BaseCollector):
    """Collects network I/O metrics."""

    def __init__(self) -> None:
        super().__init__("network")

    def _collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        counters = self.safe_get(psutil.net_io_counters)
        if counters:
            data["net_bytes_sent"] = counters.bytes_sent
            data["net_bytes_recv"] = counters.bytes_recv
            data["net_packets_sent"] = counters.packets_sent
            data["net_packets_recv"] = counters.packets_recv
            data["net_errin"] = counters.errin
            data["net_errout"] = counters.errout
            data["net_dropin"] = counters.dropin
            data["net_dropout"] = counters.dropout

        return data
