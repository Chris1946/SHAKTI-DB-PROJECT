"""
PulseTrace Developer Intelligence Platform
Stage 1-6 Entry Point UI

When the user selects a project directory:
  Stage 1 — Static analysis (AST parse via backend)
  Stage 2 — Sandbox execution (subprocess launch via backend)
  Stage 4 — Live Execution Twin (full OS topology with packets + live telemetry)
"""

import logging
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFileDialog, QProgressBar, QMessageBox
)

from desktop.ui.theme import Theme
from desktop.ui.execution_engine.engine import ExecutionEngine
from desktop.services.api_client import APIClient, APIClientError
from desktop.services.poll_worker import PollWorker

logger = logging.getLogger(__name__)


# ── Background Workers ─────────────────────────────────────────────

class AnalyzerWorker(QThread):
    """Background thread to perform static analysis so UI doesn't block."""
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.api = APIClient()

    def run(self):
        try:
            logger.info(f"Triggering static analysis on {self.path}")
            res = self.api.post("intelligence/analyze", json={"project_path": self.path})
            self.result_ready.emit(res.get("graph", {}))
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.error_occurred.emit(str(e))


class ExecuteWorker(QThread):
    """Background thread to trigger secure execution."""
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.api = APIClient()

    def run(self):
        try:
            logger.info(f"Triggering sandbox execution on {self.path}")
            res = self.api.post("intelligence/execute", json={"project_path": self.path})
            self.result_ready.emit(res)
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            self.error_occurred.emit(str(e))


class SandboxTelemetryWorker(QThread):
    """Polls real-time telemetry from the sandboxed process for authentic visualization."""
    data_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, pid: int, interval_ms: int = 250):
        super().__init__()
        self.pid = pid
        self.interval_ms = interval_ms
        self.api = APIClient()
        self._running = True

    def run(self):
        import time
        while self._running:
            try:
                res = self.api.get(f"intelligence/telemetry/{self.pid}")
                self.data_received.emit(res)
            except Exception as e:
                self.error_occurred.emit(str(e))
            time.sleep(self.interval_ms / 1000.0)

    def stop(self):
        self._running = False


# ── Main Page ──────────────────────────────────────────────────────

class IntelligenceLabPage(QWidget):
    def __init__(self, on_connection_changed=None, parent=None):
        super().__init__(parent)
        self._on_connection_changed = on_connection_changed
        self._analysis_graph = None   # Saved from Stage 1
        self._project_path = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header controls
        header_layout = QHBoxLayout()
        self.btn_learning_mode = QPushButton("🧠 Learning Mode: OFF")
        self.btn_learning_mode.setCheckable(True)
        self.btn_learning_mode.clicked.connect(self._toggle_learning)

        self.btn_dev_mode = QPushButton("🛠 Developer Mode: OFF")
        self.btn_dev_mode.setCheckable(True)
        self.btn_dev_mode.clicked.connect(self._toggle_dev)
        
        self.btn_remove_project = QPushButton("❌ Close Project")
        self.btn_remove_project.clicked.connect(self._on_remove_project)
        self.btn_remove_project.hide()

        header_layout.addWidget(self.btn_remove_project)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_learning_mode)
        header_layout.addWidget(self.btn_dev_mode)
        main_layout.addLayout(header_layout)

        # Main Stage Stack
        self.stack = QStackedWidget()

        # ── Stage 1: Upload ──
        self.upload_widget = QWidget()
        upload_layout = QVBoxLayout(self.upload_widget)
        upload_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        upload_title = QLabel("Upload Application Codebase")
        upload_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {Theme.get_color('accent')};")
        upload_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        upload_desc = QLabel(
            "Stage 1: Static Code Intelligence\n"
            "We will parse the AST to detect modules, frameworks, and architecture\n"
            "before executing in a secure sandbox."
        )
        upload_desc.setStyleSheet(f"color: {Theme.get_color('text_muted')};")
        upload_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_upload = QPushButton("Select Project Directory")
        self.btn_upload.setFixedSize(250, 40)
        self.btn_upload.clicked.connect(self._on_upload_click)

        upload_layout.addWidget(upload_title)
        upload_layout.addWidget(upload_desc)
        upload_layout.addSpacing(20)
        upload_layout.addWidget(self.btn_upload, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Stage 2: Analyzing ──
        self.analyzing_widget = QWidget()
        analyzing_layout = QVBoxLayout(self.analyzing_widget)
        analyzing_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_analyze_status = QLabel("Performing Static Analysis...")
        self.lbl_analyze_status.setStyleSheet(f"font-size: 18px; color: {Theme.get_color('accent')};")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setFixedSize(300, 10)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet(f"color: {Theme.get_color('text_muted')};")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.hide()

        self.btn_start_sandbox = QPushButton("Run in Sandbox 🚀")
        self.btn_start_sandbox.setFixedSize(250, 40)
        self.btn_start_sandbox.clicked.connect(self._on_start_sandbox_click)
        self.btn_start_sandbox.hide()

        analyzing_layout.addWidget(self.lbl_analyze_status, alignment=Qt.AlignmentFlag.AlignCenter)
        analyzing_layout.addSpacing(10)
        analyzing_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        analyzing_layout.addWidget(self.lbl_stats, alignment=Qt.AlignmentFlag.AlignCenter)
        analyzing_layout.addSpacing(20)
        analyzing_layout.addWidget(self.btn_start_sandbox, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Stage 4: Execution Twin (built lazily on first sandbox run) ──
        self.twin_widget = QWidget()
        self._twin_layout = QHBoxLayout(self.twin_widget)
        self._twin_initialized = False

        # Add widgets to stack
        self.stack.addWidget(self.upload_widget)     # index 0
        self.stack.addWidget(self.analyzing_widget)   # index 1
        self.stack.addWidget(self.twin_widget)        # index 2

        main_layout.addWidget(self.stack)

        self._apply_theme()
        Theme.theme_changed.connect(self._apply_theme)

    # ── Theme ──

    def _apply_theme(self):
        btn_css = f"""
            QPushButton {{
                background-color: {Theme.get_color('bg_surface')};
                color: {Theme.get_color('text_primary')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:checked {{
                background-color: {Theme.get_color('accent_ok')};
                color: #000000;
            }}
        """
        self.btn_learning_mode.setStyleSheet(btn_css)
        self.btn_dev_mode.setStyleSheet(btn_css)
        
        btn_remove_css = f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.get_color('text_muted')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: #ef4444;
                color: #ffffff;
                border-color: #ef4444;
            }}
        """
        self.btn_remove_project.setStyleSheet(btn_remove_css)

    def _toggle_learning(self, checked):
        if checked:
            # Mutual exclusion: turn off developer mode
            self.btn_dev_mode.setChecked(False)
            self.btn_dev_mode.setText("🛠 Developer Mode: OFF")
            self.btn_learning_mode.setText("🧠 Learning Mode: ON")
            if hasattr(self, 'inspector'):
                self.inspector.set_mode("learning")
        else:
            self.btn_learning_mode.setText("🧠 Learning Mode: OFF")
            if hasattr(self, 'inspector'):
                self.inspector.set_mode("default")

    def _toggle_dev(self, checked):
        if checked:
            # Mutual exclusion: turn off learning mode
            self.btn_learning_mode.setChecked(False)
            self.btn_learning_mode.setText("🧠 Learning Mode: OFF")
            self.btn_dev_mode.setText("🛠 Developer Mode: ON")
            if hasattr(self, 'inspector'):
                self.inspector.set_mode("developer")
        else:
            self.btn_dev_mode.setText("🛠 Developer Mode: OFF")
            if hasattr(self, 'inspector'):
                self.inspector.set_mode("default")

    # ── Stage 1: Upload ──

    def _on_upload_click(self):
        options = QFileDialog.Option.DontUseNativeDialog
        path = QFileDialog.getExistingDirectory(self, "Select Project Directory", options=options)
        if path:
            self._project_path = path
            self.btn_remove_project.show()
            self.stack.setCurrentIndex(1)
            self.lbl_analyze_status.setText(f"Analyzing {path}...")
            self.progress_bar.show()
            self.lbl_stats.hide()
            self.btn_start_sandbox.hide()

            self._worker = AnalyzerWorker(path)
            self._worker.result_ready.connect(self._on_analysis_complete)
            self._worker.error_occurred.connect(self._on_analysis_error)
            self._worker.start()

    def _on_analysis_complete(self, graph: dict):
        self._analysis_graph = graph
        self.progress_bar.hide()
        self.lbl_analyze_status.setText("✅ Static Analysis Complete")

        stats = graph.get("stats", {})
        comps = graph.get("components", {})

        stat_text = f"Parsed {stats.get('parsed_files', 0)} files • {stats.get('classes', 0)} Classes • {stats.get('functions', 0)} Functions\n"

        detected = []
        if comps.get("web_framework"):
            detected.append("🌐 Web Server")
        if comps.get("database"):
            detected.append("💾 Database")
        if comps.get("network"):
            detected.append("🔌 Network client")
        if comps.get("filesystem"):
            detected.append("📁 Filesystem")

        if detected:
            stat_text += "\nDetected: " + " | ".join(detected)

        self.lbl_stats.setText(stat_text)
        self.lbl_stats.show()

        # Apply fancy styles to start button
        self.btn_start_sandbox.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.get_color('accent')};
                color: #000;
                font-weight: bold;
                border-radius: 6px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {Theme.get_color('accent_ok')};
            }}
        """)
        self.btn_start_sandbox.show()

    def _on_analysis_error(self, err: str):
        self.progress_bar.hide()
        self.lbl_analyze_status.setText("❌ Analysis Failed")
        QMessageBox.critical(self, "Analysis Error", f"Failed to analyze project:\n{err}")
        self.stack.setCurrentIndex(0)

    # ── Stage 2: Sandbox Launch ──

    def _on_start_sandbox_click(self):
        if not self._project_path:
            return

        self.btn_start_sandbox.setText("Starting Sandbox...")
        self.btn_start_sandbox.setEnabled(False)

        self._exec_worker = ExecuteWorker(self._project_path)
        self._exec_worker.result_ready.connect(self._on_execute_complete)
        self._exec_worker.error_occurred.connect(self._on_execute_error)
        self._exec_worker.start()

    def _on_execute_complete(self, result: dict):
        self.btn_start_sandbox.setText("Run in Sandbox 🚀")
        self.btn_start_sandbox.setEnabled(True)
        
        # Save sandbox PID
        self._sandbox_pid = result.get("pid", 0)

        # Initialize the twin view if not already done
        if not self._twin_initialized:
            self._init_twin()

        # Jump to twin
        self.stack.setCurrentIndex(2)

    def _on_execute_error(self, err: str):
        self.btn_start_sandbox.setText("Run in Sandbox 🚀")
        self.btn_start_sandbox.setEnabled(True)
        # Even if sandbox launch "fails" (e.g., no entry point), still show the twin
        # since the telemetry visualization is the main value
        if not self._twin_initialized:
            self._init_twin()
        self.stack.setCurrentIndex(2)

    def _on_remove_project(self):
        self._project_path = None
        self.btn_remove_project.hide()
        
        # Stop all background threads
        self.stop_worker()
        if hasattr(self, '_worker') and self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        if hasattr(self, '_exec_worker') and self._exec_worker and self._exec_worker.isRunning():
            self._exec_worker.terminate()
            self._exec_worker.wait()
            
        # Reset UI
        self.lbl_stats.hide()
        self.btn_start_sandbox.hide()
        self.progress_bar.hide()
        self.lbl_analyze_status.setText("Performing Static Analysis...")
        
        # Reset modes
        self.btn_learning_mode.setChecked(False)
        self._toggle_learning(False)
        self.btn_dev_mode.setChecked(False)
        self._toggle_dev(False)
        
        # Recreate twin_widget to clear old layout items
        if self._twin_initialized:
            self.stack.removeWidget(self.twin_widget)
            self.twin_widget.deleteLater()
            self.twin_widget = QWidget()
            self._twin_layout = QHBoxLayout(self.twin_widget)
            self.stack.addWidget(self.twin_widget)
            self._twin_initialized = False
        
        self.stack.setCurrentIndex(0)

    # ── Stage 4: Full Twin Initialization ──

    def _init_twin(self):
        """
        Build the full OS-topology twin: nodes, edges, simulator, legend,
        inspector, and live telemetry polling — identical to DigitalTwinPage
        but inside the Intelligence Lab's stack.
        """
        from desktop.ui.execution_engine.nodes import NodeItem
        from desktop.ui.execution_engine.edges import EdgeItem
        from desktop.ui.execution_engine.simulator import TelemetrySimulator
        from desktop.ui.execution_engine.legend import LegendBox
        from desktop.ui.execution_engine.inspector import InspectorPanel
        from desktop.ui.time_machine import TimeMachine
        from desktop.ui.execution_engine.process_filter import ProcessFilterBar

        # ── Left panel: Engine + controls ──
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.engine = ExecutionEngine(self)
        left_layout.addWidget(self.engine, stretch=1)

        # ── Build the full OS topology ──
        N = NodeItem
        COL1 = -550   # Applications
        COL2 = -180   # Kernel
        COL3 =  200   # Hardware
        COL4 =  520   # External
        ROW_GAP = 100

        nodes = {
            # Column 1: User Applications
            "app":       N("app",       "User App",   "#38bdf8", icon="process",   tier="app"),
            "container": N("container", "Container",  "#06b6d4", icon="container", tier="app"),
            "database":  N("database",  "Database",   "#f472b6", icon="database",  tier="app"),

            # Column 2: Kernel Subsystems
            "syscall":   N("syscall",   "Syscall IF", "#a78bfa", icon="pipe",      tier="kernel"),
            "scheduler": N("scheduler", "Scheduler",  "#c084fc", icon="scheduler", tier="kernel"),
            "mmu":       N("mmu",       "MMU",        "#7c3aed", icon="mmu",       tier="kernel"),
            "vfs":       N("vfs",       "VFS",        "#8b5cf6", icon="vfs",       tier="kernel"),
            "netstack":  N("netstack",  "TCP/IP",     "#60a5fa", icon="tcp",       tier="network"),
            "firewall":  N("firewall",  "Firewall",   "#fb923c", icon="firewall",  tier="network"),
            "cache":     N("cache",     "Page Cache", "#e879f9", icon="cache",     tier="kernel"),
            "iosched":   N("iosched",   "I/O Sched",  "#a78bfa", icon="scheduler", tier="kernel"),

            # Column 3: Hardware
            "cpu":       N("cpu",       "CPU",        "#34d399", icon="cpu",       tier="hardware"),
            "gpu":       N("gpu",       "GPU",        "#a3e635", icon="gpu",       tier="hardware"),
            "ram":       N("ram",       "RAM",        "#2dd4bf", icon="ram",       tier="hardware"),
            "swap":      N("swap",      "Swap",       "#14b8a6", icon="swap",      tier="hardware"),
            "nic":       N("nic",       "NIC",        "#93c5fd", icon="nic",       tier="hardware"),
            "ssd":       N("ssd",       "NVMe/SSD",   "#fbbf24", icon="ssd",      tier="storage"),

            # Column 4: External
            "dns":       N("dns",       "DNS",        "#f87171", icon="dns",       tier="external"),
            "internet":  N("internet",  "Internet",   "#ef4444", icon="internet",  tier="external"),
        }

        # Position nodes
        nodes["app"].setPos(COL1,       -ROW_GAP)
        nodes["container"].setPos(COL1,  0)
        nodes["database"].setPos(COL1,   ROW_GAP)

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

        nodes["cpu"].setPos(COL3,        -ROW_GAP * 2.5)
        nodes["gpu"].setPos(COL3,        -ROW_GAP * 1.5)
        nodes["ram"].setPos(COL3,        -ROW_GAP * 0.5)
        nodes["swap"].setPos(COL3,        ROW_GAP * 0.5)
        nodes["nic"].setPos(COL3,         ROW_GAP * 1.5)
        nodes["ssd"].setPos(COL3,         ROW_GAP * 2.5)

        nodes["dns"].setPos(COL4,        -ROW_GAP * 0.5)
        nodes["internet"].setPos(COL4,    ROW_GAP * 0.5)

        for n in nodes.values():
            self.engine.add_item(n)

        # Edges
        edge_defs = [
            ("app", "syscall"), ("container", "syscall"), ("database", "syscall"), ("database", "vfs"),
            ("syscall", "scheduler"), ("syscall", "mmu"), ("syscall", "vfs"), ("syscall", "netstack"), ("syscall", "gpu"),
            ("scheduler", "cpu"),
            ("mmu", "ram"), ("mmu", "cache"), ("ram", "swap"),
            ("vfs", "cache"), ("vfs", "iosched"), ("iosched", "ssd"), ("cache", "ram"),
            ("netstack", "firewall"), ("firewall", "nic"), ("netstack", "nic"),
            ("nic", "dns"), ("nic", "internet"), ("dns", "internet"),
            ("gpu", "ram"),
        ]
        for src_id, tgt_id in edge_defs:
            if src_id in nodes and tgt_id in nodes:
                edge = EdgeItem(nodes[src_id], nodes[tgt_id])
                self.engine.add_item(edge)

        # Telemetry Simulator
        self.simulator = TelemetrySimulator(self.engine, nodes, self)

        # Legend
        self.legend = LegendBox()
        self.legend.setMaximumHeight(40)
        left_layout.addWidget(self.legend)

        # Time Machine
        self.time_machine = TimeMachine()
        left_layout.addWidget(self.time_machine)

        # Process Filter
        self.process_bar = ProcessFilterBar()
        left_layout.addWidget(self.process_bar)

        # Authenticity Indicator
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

        self._twin_layout.addLayout(left_layout, stretch=3)

        # ── Right panel: Inspector ──
        self.inspector = InspectorPanel(self)
        self._twin_layout.addWidget(self.inspector)

        # ── Wire signals ──
        self.engine.item_inspected.connect(self._on_item_inspected)
        self.time_machine.paused_changed.connect(lambda p: setattr(self.engine.time_manager, 'paused', p))
        self.time_machine.speed_changed.connect(lambda s: setattr(self.engine.time_manager, 'multiplier', s))
        self.process_bar.process_selected.connect(lambda n: self.simulator.set_process_filter(n))

        # ── Start live telemetry polling ──
        self._start_polling()

        self._twin_initialized = True
        logger.info("Intelligence Lab twin initialized with full OS topology")

    def _on_item_inspected(self, item):
        from desktop.ui.execution_engine.nodes import NodeItem
        from desktop.ui.execution_engine.packets import PacketItem

        if isinstance(item, NodeItem):
            self.inspector.inspect_node(item)
        elif isinstance(item, PacketItem):
            self.inspector.inspect_packet(item)

    def _start_polling(self):
        if not self._sandbox_pid:
            return
            
        if hasattr(self, '_poll_worker') and self._poll_worker:
            self._poll_worker.stop()
            self._poll_worker.wait()

        self._poll_worker = SandboxTelemetryWorker(self._sandbox_pid, interval_ms=250)
        self._poll_worker.data_received.connect(self._on_live_data)
        self._poll_worker.start()

    def _on_live_data(self, telemetry: dict):
        if hasattr(self, 'simulator'):
            self.simulator.update_authentic_telemetry(telemetry)

        cpu_load = telemetry.get("cpu_percent", 0.0)
        self.auth_indicator.setText(f"Hardware Authenticity: AUTHENTIC SANDBOX TELEMETRY (CPU: {cpu_load:.1f}%)")
        self.auth_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.get_color('bg_surface')};
                color: #22c55e;
                border: 1px solid {Theme.get_color('border')};
                border-radius: 4px;
                padding: 4px 8px;
                font-family: Courier;
                font-size: 10px;
                font-weight: bold;
            }}
        """)

    # ── Cleanup ──

    def stop_worker(self):
        if hasattr(self, 'engine'):
            self.engine._timer.stop()
        if hasattr(self, '_poll_worker') and self._poll_worker:
            self._poll_worker.stop()
            self._poll_worker.wait()
