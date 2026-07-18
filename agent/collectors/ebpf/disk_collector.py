"""
eBPF Disk Collector

Replaces the standard psutil disk collector with one that leverages
an eBPF probe on the block I/O layer. We read the BCC histogram to
determine latency, alongside the standard read/write byte counts.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Any

from bcc import BPF

from collectors.base import BaseCollector
import psutil

logger = logging.getLogger(__name__)


class EBPFDiskCollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__("disk")
        # 1. Load the C source
        c_path = os.path.join(os.path.dirname(__file__), "..", "..", "ebpf", "disk.c")
        with open(c_path, "r") as f:
            c_text = f.read()

        # 2. Compile and attach
        self.bpf = None
        try:
            self.bpf = BPF(text=c_text)
            self.bpf.attach_kprobe(event="blk_account_io_done", fn_name="trace_req_done")
            logger.info("eBPF Disk Collector successfully compiled and attached")
        except Exception as e:
            logger.error("Failed to compile or attach eBPF disk probe: %s. Falling back to psutil metrics.", e)
            self.bpf = None

    def _collect(self) -> Dict[str, Any]:
        """
        Merge standard psutil disk usage with eBPF latency histograms.
        """
        # We still use psutil to get capacity/usage % because eBPF is 
        # meant for tracing events (latency/bytes), not reading static filesystem capacities.
        metrics = {}
        
        try:
            usage = psutil.disk_usage("/")
            metrics.update({
                "disk_total": usage.total,
                "disk_used": usage.used,
                "disk_free": usage.free,
                "disk_percent": usage.percent,
            })
            
            io_counters = psutil.disk_io_counters()
            if io_counters:
                metrics.update({
                    "disk_read_bytes": io_counters.read_bytes,
                    "disk_write_bytes": io_counters.write_bytes,
                })
        except Exception as e:
            logger.error("Failed to read disk usage: %s", e)

        # Append eBPF histogram data
        if self.bpf:
            dist = self.bpf.get_table("dist")
            
            # Export the histogram buckets for the backend
            histogram = {}
            for k, v in dist.items():
                if v.value > 0:
                    histogram[str(k.value)] = v.value
                    
            metrics["ebpf_disk_latency_us_histogram"] = histogram
            
            # We clear the histogram every collection cycle so we get a rolling delta
            dist.clear()

        return metrics
