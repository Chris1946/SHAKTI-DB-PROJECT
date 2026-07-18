"""
eBPF Collector Package

Provides high-performance metrics collection using BCC (BPF Compiler Collection).
Will raise ImportError if BCC is not installed or if running on an incompatible OS (e.g. macOS).
"""

from __future__ import annotations

import platform

# Pre-flight check: Are we on Linux?
if platform.system() != "Linux":
    raise ImportError("eBPF collectors require a Linux kernel.")

try:
    import bcc
except ImportError:
    raise ImportError("bcc module not found. Please install BCC (BPF Compiler Collection).")

# We only import the actual collectors if the above checks pass
from .disk_collector import EBPFDiskCollector
from .network_collector import EBPFNetworkCollector

__all__ = ["EBPFDiskCollector", "EBPFNetworkCollector"]
