"""
PulseTrace Desktop — Main Application Window
=============================================

``MainWindow`` is the top-level ``QMainWindow`` shell.

Layout
------

┌──────────────────────────────────────────────────────────────────────┐
│  Sidebar (fixed 220px)   │  Content Area (stretches)                 │
│  ─────────────────────── │  ─────────────────────────────────────── │
│  [Logo / Brand]          │  page_title                               │
│                          │  page_subtitle                            │
│  ● Dashboard             │  ┌─────────────────────────────────────┐  │
│  ○ Processes             │  │  QStackedWidget (active page)        │  │
│  ○ Alerts                │  └─────────────────────────────────────┘  │
│                          │                                            │
│  ─────────────────────── │                                            │
│  [Status / Host info]    │                                            │
├──────────────────────────────────────────────────────────────────────┤
│  Status Bar (28px)  ●  Connected  │  Host: machine  │  2026-07-13    │
└──────────────────────────────────────────────────────────────────────┘

Responsibilities
----------------
- Instantiate and own each page widget.
- Route navigation events from the sidebar to the stacked widget.
- Maintain the connection-status indicator in the status bar.
- Expose ``set_status()`` so pages / services can report health.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from desktop.config import config
from desktop.pages.dashboard_page import DashboardPage
from desktop.pages.processes_page import ProcessesPage
from desktop.pages.alerts_page import AlertsPage
from desktop.pages.digital_twin_page import DigitalTwinPage
from desktop.ui.theme import Theme

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Navigation item definition
# ---------------------------------------------------------------------------

class NavItem:
    """Simple data-class that maps a sidebar label to a page index."""

    def __init__(self, label: str, icon: str, page_index: int):
        self.label = label
        self.icon = icon          # Unicode icon — no external files required
        self.page_index = page_index


# Plain-text nav items — emoji icons that render on every platform
NAV_ITEMS_PLAIN: List[NavItem] = [
    NavItem("Dashboard",  "◈", 0),
    NavItem("Processes",  "≡", 1),
    NavItem("Digital Twin", "⚗", 2),
    NavItem("Alerts",     "◉", 3),
]


# ---------------------------------------------------------------------------
# Sidebar widget
# ---------------------------------------------------------------------------

class Sidebar(QWidget):
    """
    Left navigation panel.

    Emits nothing directly — callers connect to
    ``nav_list.currentRowChanged`` to handle page switching.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setStyleSheet("")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Brand block ----
        brand_container = QWidget()
        brand_container.setStyleSheet("background: transparent;")
        brand_layout = QVBoxLayout(brand_container)
        brand_layout.setContentsMargins(18, 22, 18, 14)
        brand_layout.setSpacing(3)

        # Top row: dot + name
        top_row_widget = QWidget()
        top_row_widget.setStyleSheet("background: transparent;")
        top_row = QHBoxLayout(top_row_widget)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(7)

        dot_lbl = QLabel("⬡")
        dot_lbl.setObjectName("brand_dot")
        dot_font = QFont()
        dot_font.setPointSize(14)
        dot_font.setBold(True)
        brand_top = QHBoxLayout(top_row_widget)
        brand_top.setContentsMargins(0, 0, 0, 0)
        brand_top.setSpacing(4)

        self.brand_pulse = QLabel("PULSE")
        self.brand_pulse.setObjectName("brand_pulse")

        self.brand_dot = QLabel("●")
        self.brand_dot.setObjectName("brand_dot")

        self.brand_trace = QLabel("TRACE")
        self.brand_trace.setObjectName("brand_pulse")
        self.brand_trace.setStyleSheet("font-size: 16px; font-weight: 800; letter-spacing: 2px;")

        brand_top.addWidget(self.brand_pulse)
        brand_top.addWidget(self.brand_dot)
        brand_top.addWidget(self.brand_trace)
        brand_top.addStretch()

        brand_sub = QLabel("EBPF MONITOR")
        brand_sub.setObjectName("brand_sub")

        brand_layout.addWidget(top_row_widget)
        brand_layout.addWidget(brand_sub)
        layout.addWidget(brand_container)

        # ---- Divider ----
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setObjectName("sidebar_divider")
        layout.addWidget(divider)
        layout.addSpacing(6)

        # ---- Navigation list ----
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("nav_list")
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        for item_def in NAV_ITEMS_PLAIN:
            list_item = QListWidgetItem(f"  {item_def.icon}   {item_def.label}")
            list_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.nav_list.addItem(list_item)

        self.nav_list.setCurrentRow(0)
        layout.addWidget(self.nav_list)
        layout.addStretch()

        # ---- Theme Toggle ----
        self.btn_theme = QPushButton("Appearance: Dark" if Theme.is_dark else "Appearance: Light")
        self.btn_theme.setObjectName("btn_theme")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self._toggle_theme)
        layout.addWidget(self.btn_theme)
        layout.addSpacing(4)

        # ---- Divider above status ----
        divider2 = QWidget()
        divider2.setFixedHeight(1)
        divider2.setObjectName("sidebar_divider")
        layout.addWidget(divider2)

        # ---- Connection badge ----
        self.conn_label = QLabel("⬤  Connecting…")
        self.conn_label.setObjectName("status_indicator_warn")
        conn_font = QFont()
        conn_font.setPointSize(10)
        self.conn_label.setFont(conn_font)
        self.conn_label.setContentsMargins(18, 12, 18, 16)
        layout.addWidget(self.conn_label)

    def set_connection_status(self, connected: bool) -> None:
        """Update the small connection badge at the bottom of the sidebar."""
        if connected:
            self.conn_label.setText("⬤  Connected")
            self.conn_label.setObjectName("status_indicator_ok")
        else:
            self.conn_label.setText("⬤  Unreachable")
            self.conn_label.setObjectName("status_indicator_crit")
        # Force QSS re-evaluation after objectName change
        self.conn_label.style().unpolish(self.conn_label)
        self.conn_label.style().polish(self.conn_label)

    def _toggle_theme(self) -> None:
        Theme.toggle()
        self.btn_theme.setText("Appearance: Dark" if Theme.is_dark else "Appearance: Light")


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """
    Top-level application window.

    Sets up the two-panel splitter layout (Sidebar | Content),
    wires navigation, and maintains the global status bar.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(config.WINDOW_TITLE)
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self._build_ui()
        self._wire_navigation()
        self._start_clock()
        Theme.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        """Assemble the main layout."""

        # ---- Root container ----
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # ---- Sidebar ----
        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        # ---- Content area ----
        content_area = QWidget()
        content_area.setObjectName("content_area")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Page header (title + subtitle that update on navigation)
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        titles_layout = QVBoxLayout()
        titles_layout.setContentsMargins(0, 0, 0, 0)

        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("page_title")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        self.page_title.setFont(title_font)

        self.page_subtitle = QLabel("Real-time system performance overview")
        self.page_subtitle.setObjectName("page_subtitle")
        sub_font = QFont()
        sub_font.setPointSize(14)
        self.page_subtitle.setFont(sub_font)

        titles_layout.addWidget(self.page_title)
        titles_layout.addWidget(self.page_subtitle)
        
        header_layout.addLayout(titles_layout)
        header_layout.addStretch()
        
        self.network_btn = QPushButton(" 🛜 Network")
        self.network_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.network_btn.setObjectName("network_btn")
        self.network_btn.clicked.connect(self._show_network_menu)
        header_layout.addWidget(self.network_btn)

        content_layout.addWidget(header_widget)

        # Stacked widget — one child per page
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        self._page_meta = [
            ("Dashboard",  "Real-time system performance overview"),
            ("Processes",  "Running processes sorted by CPU usage"),
            ("Digital Twin", "OS Digital Twin Visualization"),
            ("Alerts",     "Active and historical alert events"),
        ]

        # ---- Page 0: Dashboard (real) ----
        self.dashboard_page = DashboardPage(
            on_connection_changed=self.set_connection_status
        )
        self.stack.addWidget(self.dashboard_page)

        # ---- Page 1: Processes (real) ----
        self.processes_page = ProcessesPage(
            on_connection_changed=self.set_connection_status
        )
        self.stack.addWidget(self.processes_page)

        # ---- Page 2: Digital Twin ----
        self.digital_twin_page = DigitalTwinPage(
            on_connection_changed=self.set_connection_status
        )
        self.stack.addWidget(self.digital_twin_page)

        # ---- Page 3: Alerts (real) ----
        self.alerts_page = AlertsPage(
            on_connection_changed=self.set_connection_status
        )
        self.stack.addWidget(self.alerts_page)

        root_layout.addWidget(content_area, 1)   # 1 = stretch factor

        # ---- Custom status bar ----
        self._build_status_bar()

    def _build_status_bar(self) -> None:
        """Build the slim status bar at the bottom of the window."""
        status_bar = QStatusBar(self)
        status_bar.setObjectName("status_bar")
        status_bar.setSizeGripEnabled(False)
        self.setStatusBar(status_bar)

        self._status_conn = QLabel("⬤  Connected")
        self._status_conn.setObjectName("status_indicator_ok")

        self._status_host = QLabel(f"Host: {self._hostname()}")
        self._status_host.setObjectName("status_text")

        self._status_time = QLabel()
        self._status_time.setObjectName("status_text")

        sep1 = QLabel("│")
        sep1.setObjectName("status_text")
        sep2 = QLabel("│")
        sep2.setObjectName("status_text")

        status_bar.addWidget(self._status_conn)
        status_bar.addWidget(sep1)
        status_bar.addWidget(self._status_host)
        status_bar.addPermanentWidget(sep2)
        status_bar.addPermanentWidget(self._status_time)

    def _show_network_menu(self) -> None:
        import socket
        import subprocess
        
        # Get IP
        ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
            
        # Get DNS (macOS)
        dns = "unknown"
        try:
            out = subprocess.check_output("cat /etc/resolv.conf | grep nameserver", shell=True).decode()
            for line in out.splitlines():
                if "nameserver" in line:
                    dns = line.split()[1]
                    break
        except Exception:
            pass
            
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Theme.get_color('bg_surface')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 12px;
                color: {Theme.get_color('text_primary')};
            }}
        """)
        
        menu.addAction(f"IP Address: {ip}")
        menu.addAction(f"DNS Server: {dns}")
        menu.exec_(self.network_btn.mapToGlobal(self.network_btn.rect().bottomLeft()))

    # ------------------------------------------------------------------ #
    # Navigation wiring                                                    #
    # ------------------------------------------------------------------ #

    def _wire_navigation(self) -> None:
        """Connect sidebar selection changes to the stacked widget."""
        self.sidebar.nav_list.currentRowChanged.connect(self._on_nav_changed)

    @Slot(int)
    def _on_nav_changed(self, index: int) -> None:
        """Switch the active page and update the header."""
        if 0 <= index < len(self._page_meta):
            title, subtitle = self._page_meta[index]
            self.page_title.setText(title)
            self.page_subtitle.setText(subtitle)
            self.stack.setCurrentIndex(index)
            logger.debug("Navigated to page: %s", title)

    # ------------------------------------------------------------------ #
    # Public API — called by workers / services                           #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        """Gracefully stop all background threads before the window closes."""
        logger.info("MainWindow closing — stopping workers")
        self.dashboard_page.stop_worker()
        self.processes_page.stop_worker()
        self.digital_twin_page.stop_worker()
        self.alerts_page.stop_worker()
        self.intelligence_lab_page.stop_worker()
        super().closeEvent(event)

    @Slot(bool)
    def set_connection_status(self, connected: bool) -> None:
        """Update both the sidebar badge and the status bar indicator."""
        self.sidebar.set_connection_status(connected)
        if connected:
            self._status_conn.setText("⬤  Connected")
            self._status_conn.setObjectName("status_indicator_ok")
        else:
            self._status_conn.setText("⬤  Unreachable")
            self._status_conn.setObjectName("status_indicator_crit")
        self._status_conn.style().unpolish(self._status_conn)
        self._status_conn.style().polish(self._status_conn)

    @Slot()
    def _on_theme_changed(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(Theme.get_qss())
        # Re-polish status connection badge so colors apply
        self._status_conn.style().unpolish(self._status_conn)
        self._status_conn.style().polish(self._status_conn)
        self.sidebar.conn_label.style().unpolish(self.sidebar.conn_label)
        self.sidebar.conn_label.style().polish(self.sidebar.conn_label)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _start_clock(self) -> None:
        """Tick the clock label in the status bar every second."""
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

    @Slot()
    def _tick_clock(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self._status_time.setText(now)

    @staticmethod
    def _hostname() -> str:
        import socket
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
