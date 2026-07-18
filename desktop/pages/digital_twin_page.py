"""
PulseTrace Desktop — OS Digital Twin Page
Clean, spacious layout with no AI explainer panel.
"""

from __future__ import annotations

import logging
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from desktop.ui.time_machine import TimeMachine
from desktop.services.poll_worker import PollWorker

logger = logging.getLogger(__name__)


class TwinPollWorker(PollWorker):
    from PySide6.QtCore import Signal
    data_received = Signal(list, list)

    def _fetch(self) -> None:
        try:
            metrics = self._service.get_latest_system_metrics()
            processes = self._service.get_latest_processes(limit=15)
            self._set_connection(True)
            self.data_received.emit(metrics, processes)
        except Exception:
            self._set_connection(False)

class DigitalTwinPage(QWidget):
    """
    Visualizes the OS as a live interactive graph.
    """

    def __init__(self, on_connection_changed=None, parent=None):
        super().__init__(parent)
        self._on_connection_changed = on_connection_changed
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Main: Digital Twin Execution Engine (takes most space)
        from desktop.ui.execution_engine.engine import ExecutionEngine
        self.engine = ExecutionEngine(self)
        left_layout.addWidget(self.engine, stretch=1)

        self._init_nodes()

        # Legend Box (At the bottom of the graph, part of layout)
        from desktop.ui.execution_engine.legend import LegendBox
        self.legend = LegendBox()
        self.legend.setMaximumHeight(40)
        left_layout.addWidget(self.legend)

        # Bottom controls: Time Machine + Process Filter
        self.time_machine = TimeMachine()
        left_layout.addWidget(self.time_machine)

        from desktop.ui.execution_engine.process_filter import ProcessFilterBar
        self.process_bar = ProcessFilterBar()
        left_layout.addWidget(self.process_bar)
        
        # Authenticity Indicator Overlay
        from PySide6.QtWidgets import QLabel
        from desktop.ui.theme import Theme
        self.auth_indicator = QLabel("Hardware Authenticity: CONNECTING TO AGENT...")
        self.auth_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.get_color('bg_surface')};
                color: {Theme.get_color('accent_warn')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 4px;
                padding: 4px 8px;
                font-family: Courier;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        self.auth_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.auth_indicator)

        main_layout.addLayout(left_layout, stretch=3)

        # Right: Inspector
        from desktop.ui.execution_engine.inspector import InspectorPanel
        self.inspector = InspectorPanel(self)
        main_layout.addWidget(self.inspector)

        # ── Wire signals ──
        self.engine.item_inspected.connect(self._on_item_inspected)
        self.time_machine.paused_changed.connect(self._on_pause_changed)
        self.time_machine.speed_changed.connect(self._on_speed_changed)
        self.process_bar.process_selected.connect(self._on_process_selected)

    def _on_pause_changed(self, paused: bool):
        self.engine.time_manager.paused = paused

    def _on_speed_changed(self, speed: float):
        self.engine.time_manager.multiplier = speed

    def _on_process_selected(self, name: str):
        if hasattr(self, 'simulator'):
            self.simulator.set_process_filter(name)

    def _on_item_inspected(self, item):
        from desktop.ui.execution_engine.nodes import NodeItem
        from desktop.ui.execution_engine.packets import PacketItem

        if isinstance(item, NodeItem):
            self.inspector.inspect_node(item)
        elif isinstance(item, PacketItem):
            self.inspector.inspect_packet(item)

    def _init_nodes(self):
        from desktop.ui.execution_engine.nodes import NodeItem
        from desktop.ui.execution_engine.edges import EdgeItem
        from desktop.ui.execution_engine.simulator import TelemetrySimulator

        # ══════════════════════════════════════════════════════════════
        #  SPACIOUS LAYOUT — 4 clear vertical columns, well separated
        #
        #  Col 1 (x=-600)   Col 2 (x=-200)   Col 3 (x=200)   Col 4 (x=550)
        #  ─────────────    ──────────────    ─────────────    ─────────────
        #  APPLICATIONS     KERNEL            HARDWARE         EXTERNAL
        # ══════════════════════════════════════════════════════════════

        N = NodeItem
        COL1 = -550   # Applications
        COL2 = -180   # Kernel
        COL3 =  200   # Hardware
        COL4 =  520   # External

        ROW_GAP = 100  # Vertical gap between nodes

        nodes = {
            # ── Column 1: User Applications ──
            "app":       N("app",       "User App",   "#38bdf8", icon="process",   tier="app"),
            "container": N("container", "Container",  "#06b6d4", icon="container", tier="app"),
            "database":  N("database",  "Database",   "#f472b6", icon="database",  tier="app"),

            # ── Column 2: Kernel Subsystems ──
            "syscall":   N("syscall",   "Syscall IF", "#a78bfa", icon="pipe",      tier="kernel"),
            "scheduler": N("scheduler", "Scheduler",  "#c084fc", icon="scheduler", tier="kernel"),
            "mmu":       N("mmu",       "MMU",        "#7c3aed", icon="mmu",       tier="kernel"),
            "vfs":       N("vfs",       "VFS",        "#8b5cf6", icon="vfs",       tier="kernel"),
            "netstack":  N("netstack",  "TCP/IP",     "#60a5fa", icon="tcp",       tier="network"),
            "firewall":  N("firewall",  "Firewall",   "#fb923c", icon="firewall",  tier="network"),
            "cache":     N("cache",     "Page Cache", "#e879f9", icon="cache",     tier="kernel"),
            "iosched":   N("iosched",   "I/O Sched",  "#a78bfa", icon="scheduler", tier="kernel"),

            # ── Column 3: Hardware ──
            "cpu":       N("cpu",       "CPU",        "#34d399", icon="cpu",       tier="hardware"),
            "gpu":       N("gpu",       "GPU",        "#a3e635", icon="gpu",       tier="hardware"),
            "ram":       N("ram",       "RAM",        "#2dd4bf", icon="ram",       tier="hardware"),
            "swap":      N("swap",      "Swap",       "#14b8a6", icon="swap",      tier="hardware"),
            "nic":       N("nic",       "NIC",        "#93c5fd", icon="nic",       tier="hardware"),
            "ssd":       N("ssd",       "NVMe/SSD",   "#fbbf24", icon="ssd",      tier="storage"),

            # ── Column 4: External ──
            "dns":       N("dns",       "DNS",        "#f87171", icon="dns",       tier="external"),
            "internet":  N("internet",  "Internet",   "#ef4444", icon="internet",  tier="external"),
        }

        # ── Column 1: Apps (3 nodes, centred vertically) ──
        nodes["app"].setPos(COL1,       -ROW_GAP)
        nodes["container"].setPos(COL1,  0)
        nodes["database"].setPos(COL1,   ROW_GAP)

        # ── Column 2: Kernel (7 nodes, spread across 2 sub-columns) ──
        #   Left sub-col (COL2): syscall, scheduler, mmu, vfs
        #   Right sub-col (COL2+160): netstack, firewall, cache, iosched
        KC_L = COL2
        KC_R = COL2 + 160

        nodes["syscall"].setPos(KC_L,    -ROW_GAP * 1.5)
        nodes["scheduler"].setPos(KC_L,  -ROW_GAP * 0.5)
        nodes["mmu"].setPos(KC_L,         ROW_GAP * 0.5)
        nodes["vfs"].setPos(KC_L,         ROW_GAP * 1.5)

        nodes["netstack"].setPos(KC_R,   -ROW_GAP * 1.5)
        nodes["firewall"].setPos(KC_R,   -ROW_GAP * 0.5)
        nodes["cache"].setPos(KC_R,       ROW_GAP * 0.5)
        nodes["iosched"].setPos(KC_R,     ROW_GAP * 1.5)

        # ── Column 3: Hardware (6 nodes) ──
        nodes["cpu"].setPos(COL3,        -ROW_GAP * 2.5)
        nodes["gpu"].setPos(COL3,        -ROW_GAP * 1.5)
        nodes["ram"].setPos(COL3,        -ROW_GAP * 0.5)
        nodes["swap"].setPos(COL3,        ROW_GAP * 0.5)
        nodes["nic"].setPos(COL3,         ROW_GAP * 1.5)
        nodes["ssd"].setPos(COL3,         ROW_GAP * 2.5)

        # ── Column 4: External (2 nodes) ──
        nodes["dns"].setPos(COL4,        -ROW_GAP * 0.5)
        nodes["internet"].setPos(COL4,    ROW_GAP * 0.5)

        for n in nodes.values():
            self.engine.add_item(n)

        # ── Edges ──
        edge_defs = [
            # App → Kernel
            ("app",       "syscall"),
            ("container", "syscall"),
            ("database",  "syscall"),
            ("database",  "vfs"),

            # Syscall → Kernel subsystems
            ("syscall",   "scheduler"),
            ("syscall",   "mmu"),
            ("syscall",   "vfs"),
            ("syscall",   "netstack"),
            ("syscall",   "gpu"),

            # Scheduler → CPU
            ("scheduler", "cpu"),

            # MMU → Memory
            ("mmu",       "ram"),
            ("mmu",       "cache"),
            ("ram",       "swap"),

            # VFS → Storage
            ("vfs",       "cache"),
            ("vfs",       "iosched"),
            ("iosched",   "ssd"),
            ("cache",     "ram"),

            # Network path
            ("netstack",  "firewall"),
            ("firewall",  "nic"),
            ("netstack",  "nic"),
            ("nic",       "dns"),
            ("nic",       "internet"),
            ("dns",       "internet"),

            # GPU → RAM
            ("gpu",       "ram"),
        ]

        for src_id, tgt_id in edge_defs:
            if src_id in nodes and tgt_id in nodes:
                edge = EdgeItem(nodes[src_id], nodes[tgt_id])
                self.engine.add_item(edge)

        self.simulator = TelemetrySimulator(self.engine, nodes, self)
        
        self._start_worker()

    def _start_worker(self) -> None:
        from PySide6.QtCore import QThread
        self._worker = TwinPollWorker(interval_ms=2000)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start_polling)
        self._thread.finished.connect(self._worker.deleteLater)

        self._worker.data_received.connect(self._on_live_data)
        if self._on_connection_changed is not None:
            self._worker.connection_changed.connect(self._on_connection_changed)

        self._thread.start()
        
    def _on_live_data(self, metrics, processes):
        if not metrics:
            return
        # Pass real processes and CPU load to the simulator!
        real_procs = [(p.get("name", "unknown"), p.get("pid", 0)) for p in processes if p.get("pid")]
        cpu_load = metrics[0].get("cpu_percent", 10.0)
        
        if hasattr(self, 'simulator'):
            self.simulator.update_live_telemetry(real_procs, metrics[0])
            
        from desktop.ui.theme import Theme
        self.auth_indicator.setText(f"Hardware Authenticity: LIVE KERNEL TELEMETRY (CPU: {cpu_load:.1f}%)")
        self.auth_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.get_color('bg_surface')};
                color: {Theme.get_color('accent_ok')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 4px;
                padding: 4px 8px;
                font-family: Courier;
                font-size: 10px;
                font-weight: bold;
            }}
        """)

    def stop_worker(self):
        if hasattr(self, 'engine'):
            self.engine._timer.stop()
        if hasattr(self, 'simulator'):
            self.simulator.spawn_timer.stop()
        if hasattr(self, '_worker'):
            from PySide6.QtCore import QMetaObject
            QMetaObject.invokeMethod(self._worker, "stop", Qt.ConnectionType.BlockingQueuedConnection)
            self._thread.quit()
            self._thread.wait()
