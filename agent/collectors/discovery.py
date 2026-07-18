import platform
import psutil
import json
import logging
import os

logger = logging.getLogger(__name__)

def collect_system_profile() -> dict:
    """
    Collects static and semi-static System Intelligence Profile.
    Returns a dict matching the SystemMemory schema requirements.
    """
    profile = {
        "hostname": platform.node(),
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "architecture": platform.machine(),
        "cpu_model": platform.processor() or "Unknown CPU",
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "total_memory": psutil.virtual_memory().total,
        "ebpf_support": False,
        "profile": {}
    }

    # eBPF Support check (rough approximation: Linux + root)
    if profile["os_name"] == "Linux" and os.geteuid() == 0:
        profile["ebpf_support"] = True

    # Docker/Container detection
    in_docker = os.path.exists("/.dockerenv")
    profile["profile"]["containerized"] = in_docker

    # Attempt to read NUMA nodes on Linux
    if profile["os_name"] == "Linux":
        try:
            numa_dir = "/sys/devices/system/node"
            if os.path.exists(numa_dir):
                nodes = [d for d in os.listdir(numa_dir) if d.startswith("node")]
                profile["profile"]["numa_nodes"] = len(nodes)
        except Exception as e:
            logger.debug(f"Failed to read NUMA nodes: {e}")

    return profile
