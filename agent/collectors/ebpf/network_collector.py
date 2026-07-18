"""
eBPF Network Collector

Replaces the standard psutil network collector by reading kernel TCP connection
latency histograms directly from eBPF maps, in addition to standard byte counts.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Any

from bcc import BPF

from collectors.base import BaseCollector
import psutil

logger = logging.getLogger(__name__)


class EBPFNetworkCollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__("network")
        
        c_path = os.path.join(os.path.dirname(__file__), "..", "..", "ebpf", "network.c")
        with open(c_path, "r") as f:
            c_text = f.read()

        self.bpf = None
        try:
            self.bpf = BPF(text=c_text)
            self.bpf.attach_kprobe(event="tcp_v4_connect", fn_name="trace_connect_entry")
            self.bpf.attach_kretprobe(event="tcp_v4_connect", fn_name="trace_connect_return")
            logger.info("eBPF Network Collector successfully compiled and attached")
        except Exception as e:
            logger.error("Failed to compile or attach eBPF network probe: %s. Falling back to psutil metrics.", e)
            self.bpf = None

    def _collect(self) -> Dict[str, Any]:
        """Merge psutil bytes with eBPF TCP connection latency."""
        metrics = {}
        
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.update({
                    "net_bytes_sent": net_io.bytes_sent,
                    "net_bytes_recv": net_io.bytes_recv,
                    "net_packets_sent": net_io.packets_sent,
                    "net_packets_recv": net_io.packets_recv,
                    "net_errin": net_io.errin,
                    "net_errout": net_io.errout,
                    "net_dropin": net_io.dropin,
                    "net_dropout": net_io.dropout,
                })
        except Exception as e:
            logger.error("Failed to read net_io: %s", e)

        # Append eBPF histogram
        if self.bpf:
            hist = self.bpf.get_table("tcp_latency_us")
            histogram = {}
            for k, v in hist.items():
                if v.value > 0:
                    histogram[str(k.value)] = v.value
                    
            metrics["ebpf_tcp_latency_us_histogram"] = histogram
            
            # Reset bucket counts for next polling cycle
            hist.clear()

        return metrics
