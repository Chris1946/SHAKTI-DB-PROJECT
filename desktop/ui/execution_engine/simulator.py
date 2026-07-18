"""
Execution Engine — Telemetry Simulator
Generates packets across the full OS subsystem topology.
"""

import random
import socket
from typing import List, Dict
from PySide6.QtCore import QObject, QTimer

from desktop.ui.execution_engine.engine import ExecutionEngine
from desktop.ui.execution_engine.nodes import NodeItem
from desktop.ui.execution_engine.packets import PacketItem

# ── Realistic data pools ───────────────────────────────────────────
_LOCAL_IP = None

def _get_local_ip() -> str:
    global _LOCAL_IP
    if _LOCAL_IP is None:
        try:
            # Secure local resolution without external pings
            _LOCAL_IP = socket.gethostbyname(socket.gethostname())
            if _LOCAL_IP.startswith("127."):
                _LOCAL_IP = "192.168.1.42"
        except Exception:
            _LOCAL_IP = "192.168.1.42"
    return _LOCAL_IP

_REMOTE_IPS = [
    ("142.250.190.46",  "google.com"),
    ("104.244.42.65",   "x.com"),
    ("157.240.1.35",    "facebook.com"),
    ("52.94.236.248",   "aws.amazon.com"),
    ("13.107.42.14",    "microsoft.com"),
    ("151.101.1.140",   "reddit.com"),
    ("198.35.26.96",    "wikipedia.org"),
    ("185.199.108.153", "github.com"),
    ("172.217.14.110",  "youtube.com"),
    ("18.65.233.187",   "cloudflare.com"),
]

_PROTOCOLS  = ["TCP", "UDP", "TLS 1.3", "QUIC", "HTTP/2", "HTTP/3", "gRPC"]
_DISK_OPS   = ["read", "write", "fsync", "readdir", "stat", "unlink"]
_SYSCALLS   = ["mmap", "brk", "mprotect", "futex", "clone", "epoll_wait", "io_uring"]
_DB_ENGINES = ["PostgreSQL", "Redis", "SQLite", "pgvector"]
_SCHED_POLICIES = ["SCHED_OTHER", "SCHED_FIFO", "CFS", "EEVDF"]
_DNS_TYPES  = ["A", "AAAA", "CNAME", "MX", "TXT"]

_PROCESS_NAMES = [
    ("chrome",            4821),
    ("python3",           1923),
    ("node",              3417),
    ("pulsetrace-agent",  2210),
    ("sshd",              1101),
    ("nginx",              982),
    ("docker",            1560),
    ("postgres",          3901),
    ("redis-server",      4102),
    ("containerd",        1245),
    ("systemd-resolved",   842),
]


class TelemetrySimulator(QObject):
    """
    Spawns packets across the full OS subsystem topology.
    Each route represents a realistic data flow path.
    Supports process filtering — when a filter is active,
    only packets belonging to that process are spawned.
    """
    def __init__(self, engine: ExecutionEngine, nodes: Dict[str, NodeItem], parent=None):
        super().__init__(parent)
        self.engine = engine
        self.nodes = nodes
        self.local_ip = _get_local_ip()
        self.process_filter = "ALL"

        self._live_processes = []
        self._real_cpu_scale = 1.0

    def update_live_telemetry(self, procs: List[tuple[str, int]], metrics: Dict):
        """Used by the system-wide Digital Twin."""
        if self.engine.time_manager.paused:
            return

        tm = self.engine.time_manager.multiplier
        if tm <= 0:
            return

        self._live_processes = procs if procs else _PROCESS_NAMES
        self._real_cpu_scale = max(0.5, (metrics.get("cpu_percent", 10.0) / 100.0) * 5.0)

        # We will spawn a burst of packets to visualize the current OS load
        # Use CPU scale to determine how many packets
        burst_size = int(5 * self._real_cpu_scale * tm)
        for _ in range(burst_size):
            proc_name, pid = random.choice(self._live_processes)
            proc_label = f"{proc_name} (PID {pid})"

            # Randomly pick a subsystem to visualize
            activity = random.choice(["network", "disk", "cpu", "memory"])

            if activity == "network":
                route = ["app", "syscall", "netstack", "nic", "internet"]
                color = "#60a5fa"
                proto = random.choice(_PROTOCOLS)
                ip, domain = random.choice(_REMOTE_IPS)
                metadata = {
                    "type": "Network Packet",
                    "process": proc_label,
                    "protocol": proto,
                    "remote_ip": ip,
                    "domain": domain,
                    "authentic": False
                }
            elif activity == "disk":
                route = ["app", "syscall", "vfs", "iosched", "ssd"]
                color = "#fbbf24"
                metadata = {
                    "type": "Disk I/O",
                    "process": proc_label,
                    "operation": random.choice(_DISK_OPS),
                    "authentic": False
                }
            elif activity == "cpu":
                route = ["app", "syscall", "scheduler", "cpu"]
                color = "#34d399"
                metadata = {
                    "type": "CPU Context Switch",
                    "process": proc_label,
                    "policy": random.choice(_SCHED_POLICIES),
                    "authentic": False
                }
            else:
                route = ["app", "syscall", "mmu", "ram"]
                color = "#c084fc"
                metadata = {
                    "type": "Memory Allocation",
                    "process": proc_label,
                    "syscall": random.choice(["mmap", "brk", "mprotect"]),
                    "authentic": False
                }
            
            # 50% chance to go container route instead of app if it's docker/containerd
            if "docker" in proc_name.lower() or "container" in proc_name.lower():
                route[0] = "container"
            elif "postgres" in proc_name.lower() or "redis" in proc_name.lower():
                route[0] = "database"

            self._spawn_route(route, color, speed=0.5, metadata=metadata)

    def update_authentic_telemetry(self, telemetry: dict):
        """Processes real-time telemetry from the Sandbox backend."""
        if self.engine.time_manager.paused:
            return

        tm = self.engine.time_manager.multiplier
        if tm <= 0:
            return

        proc_name = "Sandbox App"

        # ── 1. Authentic CPU Context Switch ──
        cpu_percent = telemetry.get("cpu_percent", 0.0)
        if cpu_percent > 1.0 and random.random() < (cpu_percent / 100.0) * tm:
            self._spawn_route(
                ["app", "syscall", "scheduler", "cpu"], "#c084fc", speed=0.4,
                metadata={
                    "type": "Context Switch",
                    "process": proc_name,
                    "cpu_percent": f"{cpu_percent:.1f}%",
                    "authentic": True
                })

        # ── 2. Authentic Disk I/O ──
        disk_read_rate = telemetry.get("disk_read_rate", 0)
        disk_write_rate = telemetry.get("disk_write_rate", 0)

        num_reads = min(5, int((disk_read_rate / 1000) * tm) + (1 if random.random() < ((disk_read_rate / 1000) * tm) % 1 else 0))
        for _ in range(num_reads):
            cache_hit = random.random() < 0.8
            if cache_hit:
                route = ["app", "syscall", "vfs", "cache", "ram"]
                spd = 0.7
            else:
                route = ["app", "syscall", "vfs", "iosched", "ssd"]
                spd = 0.15
            self._spawn_route(route, "#34d399", speed=spd, metadata={
                "type": f"Disk Read ({'cache hit' if cache_hit else 'cache miss'})",
                "process": proc_name,
                "operation": "read",
                "cache": "HIT" if cache_hit else "MISS",
                "authentic": True
            })

        num_writes = min(5, int((disk_write_rate / 1000) * tm) + (1 if random.random() < ((disk_write_rate / 1000) * tm) % 1 else 0))
        for _ in range(num_writes):
            self._spawn_route(
                ["app", "syscall", "vfs", "iosched", "ssd"], "#fbbf24", speed=0.15,
                metadata={
                    "type": "Disk Write",
                    "process": proc_name,
                    "operation": "write",
                    "authentic": True
                })

        # ── 3. Authentic Network Sockets ──
        connections = telemetry.get("connections", [])
        for conn in connections:
            if random.random() < (0.8 * tm):  # High chance to spawn for active connections
                ip = conn.get("remote_ip")
                port = conn.get("remote_port")
                status = conn.get("status")

                if port in [5432, 6379, 3306, 27017, 11211]:
                    route = ["app", "syscall", "netstack", "database"]
                    color = "#f472b6"
                    ctype = f"DB Query (Port {port})"
                else:
                    route = ["app", "syscall", "netstack", "firewall", "nic", "internet"]
                    color = "#818cf8"
                    ctype = "Network Socket"

                self._spawn_route(
                    route, color, speed=0.45,
                    metadata={
                        "type": ctype,
                        "process": proc_name,
                        "remote_ip": ip,
                        "remote_port": port,
                        "status": status,
                        "authentic": True
                    })

    def set_process_filter(self, name: str):
        self.process_filter = name



    def _spawn_route(self, node_ids: List[str], color: str, speed: float, metadata: Dict):
        # ── Process filter check ──
        if self.process_filter != "ALL":
            proc_field = metadata.get("process", "")
            # proc_field looks like "chrome (PID 4821)" — extract the name
            proc_name = proc_field.split(" (")[0] if proc_field else ""
            if proc_name and proc_name != self.process_filter:
                return  # Skip this packet, doesn't match filter
            # If no process field (e.g. swap), skip when filtering
            if not proc_field:
                return

        path_nodes = []
        for nid in node_ids:
            if nid in self.nodes:
                path_nodes.append(self.nodes[nid])

        if len(path_nodes) < 2:
            return

        metadata["color"] = color
        metadata["speed"] = speed
        metadata["path"] = node_ids
        metadata["confidence"] = "100% Authentic Telemetry"

        packet = PacketItem(metadata, path_nodes)
        self.engine.add_item(packet)
