"""
PulseTrace Desktop — Dashboard Page
=====================================

Overview page — 3×2 card grid + live charts.

Layout
------
  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │  CPU      │  │  MEMORY   │  │  DISK     │
  └───────────┘  └───────────┘  └───────────┘
  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │  NETWORK  │  │  TEMP °C  │  │  THROTTLE │
  └───────────┘  └───────────┘  └───────────┘
  ┌──────────────────────────────────────────┐
  │  System Load chart (CPU % + Memory %)    │
  └──────────────────────────────────────────┘
  ┌──────────────────────────────────────────┐
  │  Disk I/O chart (Read + Write bytes/s)   │
  └──────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from PySide6.QtCore import Qt, QThread, Slot, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from desktop.services.poll_worker import PollWorker
from desktop.widgets.stat_card import StatCard
from desktop.ui.theme import Theme
from desktop.widgets.timeseries import TimeSeriesWidget
from desktop.widgets.speed_test import SpeedTestWidget

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(b: float, suffix: str = "B") -> str:
    """SI units (÷1000) — matches macOS Finder / System Settings for disk."""
    for unit in ("", "K", "M", "G", "T"):
        if abs(b) < 1000.0:
            return f"{b:.1f} {unit}{suffix}"
        b /= 1000.0
    return f"{b:.1f} P{suffix}"


def _fmt_bytes_bin(b: float, suffix: str = "B") -> str:
    """Binary units (÷1024) — matches Activity Monitor for RAM."""
    for unit in ("", "K", "M", "G", "T"):
        if abs(b) < 1024.0:
            return f"{b:.1f} {unit}{suffix}"
        b /= 1024.0
    return f"{b:.1f} P{suffix}"


def _safe(value, default=0.0):
    """Return value if not None, else default."""
    return value if value is not None else default

# ---------------------------------------------------------------------------
# Dashboard Poll Worker
# ---------------------------------------------------------------------------

class DashboardPollWorker(PollWorker):
    """Fetches both system metrics and top processes."""
    data_received = Signal(list, list)  # (metrics, processes)

    @Slot()
    def _fetch(self) -> None:
        try:
            metrics = self._service.get_latest_system_metrics()
            processes = self._service.get_latest_processes(limit=5)
            self._set_connection(True)
            self.data_received.emit(metrics, processes)
            logger.debug("Fetched dashboard data")
        except Exception as exc:
            from desktop.services.api_client import APIClientError
            if isinstance(exc, APIClientError):
                self._set_connection(False)
                self.error_occurred.emit(str(exc))
            logger.warning("Dashboard poll failed: %s", exc)


# ---------------------------------------------------------------------------
# Dashboard Page
# ---------------------------------------------------------------------------

class DashboardPage(QWidget):
    """
    Overview dashboard with 6 stat cards + 2 live charts.

    Parameters
    ----------
    on_connection_changed:  Callable(bool) → MainWindow.set_connection_status
    """

    def __init__(
        self,
        on_connection_changed=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_connection_changed = on_connection_changed
        self._prev_disk: Dict[str, float] = {}
        self._live_updates = True
        self._build_ui()
        self._start_worker()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(16)

        # ---- 3×2 Card Grid ----
        self._stat_cpu      = StatCard("CPU USAGE",    unit="%",  icon="⚡", accent="#d4a56a")
        self._stat_mem      = StatCard("MEMORY",       unit="%",  icon="◆",  accent="#c084fc")
        self._stat_disk     = StatCard("DISK",         unit="%",  icon="◎",  accent="#34d399")
        self._stat_net_in   = StatCard("NETWORK IN",   unit=" B", icon="↓",  accent="#60a5fa")
        self._stat_temp     = StatCard("TEMPERATURE",  unit="°C", icon="🌡", accent="#fb923c")
        self._stat_throttle = StatCard("THROTTLE",     unit="",   icon="⏱",  accent="#f87171")

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.addWidget(self._stat_cpu,      0, 0)
        grid.addWidget(self._stat_mem,      0, 1)
        grid.addWidget(self._stat_disk,     0, 2)
        grid.addWidget(self._stat_net_in,   1, 0)
        grid.addWidget(self._stat_temp,     1, 1)
        grid.addWidget(self._stat_throttle, 1, 2)
        layout.addLayout(grid)

        # ---- Controls ----
        controls = QHBoxLayout()
        self._btn_toggle_live = QPushButton("⏸ Pause Live Graphs")
        self._btn_toggle_live.setCheckable(True)
        self._btn_toggle_live.clicked.connect(self._toggle_live)
        self._btn_toggle_live.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.get_color('bg_alt')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                color: {Theme.get_color('text_primary')};
            }}
            QPushButton:checked {{
                background-color: {Theme.get_color('accent')};
                color: #ffffff;
            }}
        """)
        controls.addStretch()
        controls.addWidget(self._btn_toggle_live)
        layout.addLayout(controls)

        # ---- System Load chart ----
        self._chart_load = self._make_chart_group(
            "System Load  —  last 10 min",
            min_height=220,
        )
        self._ts_load = TimeSeriesWidget(max_points=120, y_min=0, y_max=100)
        self._cpu_series = self._ts_load.add_series("CPU %",    colour="#d4a56a")
        self._mem_series = self._ts_load.add_series("Memory %", colour="#c084fc")
        self._chart_load.layout().addWidget(self._ts_load)
        layout.addWidget(self._chart_load)

        # ---- Disk I/O chart ----
        self._chart_disk = self._make_chart_group(
            "Disk I/O  —  bytes per second",
            min_height=180,
        )
        self._ts_disk = TimeSeriesWidget(max_points=120, y_min=0, y_max=100_000_000)
        self._disk_read_series  = self._ts_disk.add_series("Read",  colour="#34d399")
        self._disk_write_series = self._ts_disk.add_series("Write", colour="#fbbf24")
        self._chart_disk.layout().addWidget(self._ts_disk)
        layout.addWidget(self._chart_disk)

        # ---- Network I/O chart ----
        self._chart_net = self._make_chart_group(
            "Network I/O  —  bytes per second",
            min_height=180,
        )
        self._ts_net = TimeSeriesWidget(max_points=120, y_min=0, y_max=100_000_000)
        self._net_recv_series = self._ts_net.add_series("Received", colour="#60a5fa")
        self._net_sent_series = self._ts_net.add_series("Sent",     colour="#f472b6")
        self._chart_net.layout().addWidget(self._ts_net)
        layout.addWidget(self._chart_net)

        # ---- Bottom Row: Top Processes + Speed Test ----
        bottom_row = QHBoxLayout()
        
        # Top Processes
        self._proc_group = self._make_chart_group("Top Processes (CPU)", min_height=180)
        self._proc_table = QTableWidget(0, 4)
        self._proc_table.setHorizontalHeaderLabels(["PID", "Name", "CPU %", "Mem %"])
        self._proc_table.horizontalHeader().setStretchLastSection(True)
        self._proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._proc_table.verticalHeader().setVisible(False)
        self._proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._proc_table.setShowGrid(False)
        self._proc_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._proc_group.layout().addWidget(self._proc_table)
        bottom_row.addWidget(self._proc_group, stretch=2)
        
        # Speed Test
        self._speed_test = SpeedTestWidget()
        bottom_row.addWidget(self._speed_test, stretch=1)
        
        layout.addLayout(bottom_row)

        layout.addStretch()

    @staticmethod
    def _make_chart_group(title: str, min_height: int = 200) -> QGroupBox:
        group = QGroupBox(title)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        group.setMinimumHeight(min_height)
        inner = QVBoxLayout(group)
        inner.setContentsMargins(8, 8, 8, 8)
        return group

    # ------------------------------------------------------------------ #
    # Background worker                                                    #
    # ------------------------------------------------------------------ #

    def _start_worker(self) -> None:
        self._worker = DashboardPollWorker()
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start_polling)
        self._thread.finished.connect(self._worker.deleteLater)

        self._worker.data_received.connect(self._on_data_received)
        if self._on_connection_changed is not None:
            self._worker.connection_changed.connect(self._on_connection_changed)
        self._worker.error_occurred.connect(self._on_error)

        self._thread.start()
        logger.info("DashboardPage: poll worker thread started")

    def stop_worker(self) -> None:
        """Gracefully shut down the background thread."""
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self._worker, "stop", Qt.ConnectionType.BlockingQueuedConnection
        )
        self._thread.quit()
        self._thread.wait()
        logger.info("DashboardPage: poll worker thread stopped")

    # ------------------------------------------------------------------ #
    # Slots                                                                #
    # ------------------------------------------------------------------ #

    @Slot()
    def _toggle_live(self) -> None:
        self._live_updates = not self._btn_toggle_live.isChecked()
        if self._live_updates:
            self._btn_toggle_live.setText("⏸ Pause Live Graphs")
        else:
            self._btn_toggle_live.setText("▶ Resume Live Graphs")

    @Slot(list, list)
    def _on_data_received(self, metrics: List[Dict[str, Any]], processes: List[Dict[str, Any]]) -> None:
        if not metrics:
            return
        m = metrics[0]
        self._apply_stat_cards(m)
        
        if self._live_updates:
            self._apply_load_chart(m)
            self._apply_disk_chart(m)
            self._apply_net_chart(m)
            self._apply_top_processes(processes)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        logger.warning("Dashboard poll error: %s", message)

    # ------------------------------------------------------------------ #
    # Metric application                                                   #
    # ------------------------------------------------------------------ #

    def _apply_stat_cards(self, m: Dict[str, Any]) -> None:
        cpu_pct   = _safe(m.get("cpu_percent"),    0.0)
        mem_pct   = _safe(m.get("memory_percent"), 0.0)
        mem_used  = _safe(m.get("memory_used"),    0)
        mem_total = _safe(m.get("memory_total"),   1)
        disk_pct  = _safe(m.get("disk_percent"),   0.0)
        disk_free = _safe(m.get("disk_free"),      0)
        net_recv  = _safe(m.get("net_bytes_recv"), 0)

        la1  = _safe(m.get("load_avg_1"),  0.0)
        la5  = _safe(m.get("load_avg_5"),  0.0)
        la15 = _safe(m.get("load_avg_15"), 0.0)

        # Make sure the chart updates its grid colors if the theme changed
        if hasattr(self, "_net_chart"):
            self._net_chart.update_theme()

        self._stat_cpu.update_value(
            cpu_pct,
            sub=f"Load: {la1:.2f} · {la5:.2f} · {la15:.2f}",
        )
        self._stat_mem.update_value(
            mem_pct,
            sub=f"{_fmt_bytes_bin(mem_used)} / {_fmt_bytes_bin(mem_total)}",
        )
        self._stat_disk.update_value(
            disk_pct,
            sub=f"{_fmt_bytes(disk_free)} free",
        )

        net_str = _fmt_bytes(net_recv)
        self._stat_net_in.update_value(
            float(net_recv), sub="Total received",
            bar_value=0, raw_label=net_str,
        )

        # Temperature card
        temp = m.get("cpu_temp_current")
        temp_high = _safe(m.get("cpu_temp_high"), 80.0)
        if temp is not None:
            pct = min(100, (temp / temp_high) * 100)
            self._stat_temp.update_value(
                temp, sub=f"High: {temp_high:.0f}°C", bar_value=pct,
            )
        else:
            self._stat_temp.update_value(0, raw_label="N/A", sub="No sensor data", bar_value=0)

        # Throttle card
        throttled = m.get("cpu_throttled")
        if throttled is True:
            self._stat_throttle.update_value(
                100, raw_label="Throttled", sub="CPU frequency reduced", bar_value=100,
                color=Theme.get_color("accent_err")
            )
        elif throttled is False:
            freq = _safe(m.get("cpu_freq_mhz"), 0)
            self._stat_throttle.update_value(
                0, raw_label="Normal", sub=f"{freq:.0f} MHz", bar_value=0,
            )
        else:
            self._stat_throttle.update_value(
                0, raw_label="N/A", sub="No throttle data", bar_value=0,
            )

    def _apply_load_chart(self, m: Dict[str, Any]) -> None:
        self._ts_load.push(self._cpu_series, _safe(m.get("cpu_percent"),    0.0))
        self._ts_load.push(self._mem_series, _safe(m.get("memory_percent"), 0.0))

    def _apply_disk_chart(self, m: Dict[str, Any]) -> None:
        read_bytes  = _safe(m.get("disk_read_bytes"),  0)
        write_bytes = _safe(m.get("disk_write_bytes"), 0)

        prev_read  = self._prev_disk.get("read",  read_bytes)
        prev_write = self._prev_disk.get("write", write_bytes)

        delta_read  = max(0.0, read_bytes  - prev_read)
        delta_write = max(0.0, write_bytes - prev_write)

        self._prev_disk["read"]  = read_bytes
        self._prev_disk["write"] = write_bytes

        self._ts_disk.push(self._disk_read_series,  delta_read)
        self._ts_disk.push(self._disk_write_series, delta_write)

    def _apply_net_chart(self, m: Dict[str, Any]) -> None:
        recv_bytes = _safe(m.get("net_bytes_recv"), 0)
        sent_bytes = _safe(m.get("net_bytes_sent"), 0)

        prev_recv = self._prev_disk.get("net_recv", recv_bytes)
        prev_sent = self._prev_disk.get("net_sent", sent_bytes)

        delta_recv = max(0.0, recv_bytes - prev_recv)
        delta_sent = max(0.0, sent_bytes - prev_sent)

        self._prev_disk["net_recv"] = recv_bytes
        self._prev_disk["net_sent"] = sent_bytes

        self._ts_net.push(self._net_recv_series, delta_recv)
        self._ts_net.push(self._net_sent_series, delta_sent)

    def _apply_top_processes(self, processes: List[Dict[str, Any]]) -> None:
        self._proc_table.setRowCount(len(processes))
        for row, proc in enumerate(processes):
            pid = QTableWidgetItem(str(proc.get("pid", "")))
            pid.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            name = QTableWidgetItem(proc.get("name", ""))
            
            cpu = QTableWidgetItem(f"{proc.get('cpu_percent', 0.0):.1f}%")
            cpu.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            mem = QTableWidgetItem(f"{proc.get('memory_percent', 0.0):.1f}%")
            mem.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            self._proc_table.setItem(row, 0, pid)
            self._proc_table.setItem(row, 1, name)
            self._proc_table.setItem(row, 2, cpu)
            self._proc_table.setItem(row, 3, mem)
