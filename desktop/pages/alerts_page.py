"""
PulseTrace Desktop — Alerts Page
==================================

A scrollable feed of system alerts, displaying active and
recently resolved threshold violations.

Layout
------

  ┌──────────────────────────────────────────────────────────────────┐
  │  [ ↺ Refresh ]    [x] Show Resolved           12 active alerts   │
  ├──────────────────────────────────────────────────────────────────┤
  │  ┌────────────────────────────────────────────────────────────┐  │
  │  │  [ ● CRITICAL ]  cpu  —  CPU usage at 95% (threshold: 90%) │  │
  │  │  Hostname: web-01    Time: 10:42:01        [ RESOLVE ]     │  │
  │  └────────────────────────────────────────────────────────────┘  │
  │  ┌────────────────────────────────────────────────────────────┐  │
  │  │  [ ● WARNING  ]  memory — Memory at 85%    [ RESOLVED ]    │  │
  │  └────────────────────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from desktop.services.poll_worker import PollWorker
from desktop.services.metric_service import MetricService
from desktop.widgets.alert_badge import AlertBadge
from desktop.widgets.diagnostic_dialog import DiagnosticDialog
from desktop.ui.theme import Theme

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert Feed Item Widget
# ---------------------------------------------------------------------------

class AlertItemWidget(QFrame):
    """
    A single alert card in the feed.
    """

    def __init__(self, alert_data: Dict[str, Any], on_resolve, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.alert_data = alert_data
        self._on_resolve = on_resolve
        
        severity = alert_data.get("severity", "info").lower()
        if severity == "critical":
            accent_color = Theme.get_color("accent_err")
        elif severity == "warning":
            accent_color = Theme.get_color("accent_warn")
        else:
            accent_color = Theme.get_color("accent_ok")

        self.setObjectName("AlertItem")
        bg_surface = Theme.get_color("bg_surface")
        border = Theme.get_color("border")
        self.setStyleSheet(f"""
            QFrame#AlertItem {{
                background-color: {bg_surface};
                border: 1px solid {border};
                border-radius: 10px;
                border-left: 6px solid {accent_color};
            }}
            QFrame#AlertItem:hover {{
                border: 1px solid {accent_color};
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Top row: Badge + Category + Time
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        
        severity = alert_data.get("severity", "info")
        badge = AlertBadge(severity=severity)
        top_row.addWidget(badge)
        
        category = alert_data.get("category", "unknown").upper()
        cat_label = QLabel(category)
        cat_label.setStyleSheet(f"color: {Theme.get_color('text_muted')}; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        top_row.addWidget(cat_label)

        top_row.addStretch()

        # Format time cleanly
        created_at = alert_data.get("created_at", "")
        if "T" in created_at:
            time_str = created_at.split("T")[1][:8]
        else:
            time_str = created_at

        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"color: {Theme.get_color('text_muted')}; font-size: 11px;")
        top_row.addWidget(time_label)
        
        layout.addLayout(top_row)

        # Middle row: Message + Resolve Button
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)
        
        msg_label = QLabel(alert_data.get("message", ""))
        msg_label.setStyleSheet(f"color: {Theme.get_color('text_primary')}; font-size: 14px;")
        msg_label.setWordWrap(True)
        mid_row.addWidget(msg_label, 1)

        self.btn_analyze = QPushButton("AI Analyze")
        self.btn_analyze.setFixedWidth(110)
        self.btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.get_color('accent')};
                color: white;
                border-radius: 6px;
                font-weight: 700;
                padding: 6px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        self.btn_analyze.clicked.connect(self._handle_analyze)
        mid_row.addWidget(self.btn_analyze)

        self.btn_resolve = QPushButton()
        self.btn_resolve.setObjectName("secondary")
        self.btn_resolve.setFixedWidth(90)

        is_resolved = alert_data.get("resolved", False)
        if is_resolved:
            self.btn_resolve.setText("Done")
            self.btn_resolve.setEnabled(False)
            self.btn_resolve.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Theme.get_color('accent_ok')};
                    border: 1px solid {Theme.get_color('accent_ok')};
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                }}
            """)
        else:
            self.btn_resolve.setText("Resolve")
            self.btn_resolve.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_resolve.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.get_color('bg_alt')};
                    color: {Theme.get_color('text_primary')};
                    border: 1px solid {Theme.get_color('border')};
                    border-radius: 6px;
                    font-weight: 600;
                    padding: 6px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.get_color('border')};
                }}
            """)
            self.btn_resolve.clicked.connect(self._handle_resolve)

        mid_row.addWidget(self.btn_resolve)
        layout.addLayout(mid_row)

        # Bottom: hostname
        hostname = alert_data.get("hostname", "unknown")
        host_label = QLabel(f"▪  {hostname}")
        host_label.setStyleSheet(f"color: {Theme.get_color('text_secondary')}; font-size: 12px;")
        layout.addWidget(host_label)

    def _handle_analyze(self) -> None:
        alert_id = self.alert_data.get("id")
        if alert_id is None:
            return

        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")

        try:
            service = MetricService()
            result = service.analyze_alert(alert_id)

            # Find the AlertsPage ancestor and pause its poll worker
            # so the feed doesn't refresh and destroy us while the dialog is open.
            alerts_page = self._find_alerts_page()
            if alerts_page:
                alerts_page.pause_polling()

            # Parent to the top-level window so the dialog survives feed rebuilds
            dialog = DiagnosticDialog(result, parent=self.window())
            dialog.setModal(True)
            dialog.exec()

            # Resume polling after the user closes the dialog
            if alerts_page:
                alerts_page.resume_polling()

        except RuntimeError:
            pass  # Widget was deleted during dialog
        except Exception as e:
            try:
                QMessageBox.warning(self, "AI Error", f"Failed to analyze: {e}")
            except RuntimeError:
                pass
        finally:
            try:
                self.btn_analyze.setEnabled(True)
                self.btn_analyze.setText("AI Analyze")
            except RuntimeError:
                pass  # Widget already deleted

    def _find_alerts_page(self):
        """Walk up the widget tree to find the parent AlertsPage."""
        widget = self.parent()
        while widget is not None:
            if isinstance(widget, AlertsPage):
                return widget
            widget = widget.parent()
        return None

    def _handle_resolve(self) -> None:
        alert_id = self.alert_data.get("id")
        if alert_id is not None:
            self.btn_resolve.setEnabled(False)
            self.btn_resolve.setText("Resolving...")
            self._on_resolve(alert_id)


# ---------------------------------------------------------------------------
# Alerts Poll Worker
# ---------------------------------------------------------------------------

class AlertPollWorker(PollWorker):
    """
    Fetches the alert feed.
    """

    def __init__(self, interval_ms: int | None = None) -> None:
        super().__init__(interval_ms)

    @Slot()
    def _fetch(self) -> None:  # type: ignore[override]
        try:
            data = self._service.get_alerts()
            self._set_connection(True)
            self.metrics_received.emit(data)
            logger.debug("Fetched %d alerts", len(data))
        except Exception as exc:
            from desktop.services.api_client import APIClientError
            if isinstance(exc, APIClientError):
                self._set_connection(False)
                self.error_occurred.emit(str(exc))
            logger.warning("Alert poll failed: %s", exc)


# ---------------------------------------------------------------------------
# Alerts Page
# ---------------------------------------------------------------------------

class AlertsPage(QWidget):
    """
    Alerts feed page.
    """

    def __init__(
        self,
        on_connection_changed=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_connection_changed = on_connection_changed
        self._alerts_data: List[Dict[str, Any]] = []
        self._service = MetricService()
        
        self._build_ui()
        self._start_worker()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(12)

        # ---- Toolbar ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(16)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.setObjectName("secondary")
        self._btn_refresh.setFixedWidth(100)
        self._btn_refresh.clicked.connect(self._manual_refresh)
        toolbar.addWidget(self._btn_refresh)

        self._chk_resolved = QCheckBox("Show resolved")
        self._chk_resolved.setChecked(True)
        self._chk_resolved.stateChanged.connect(self._render_feed)
        toolbar.addWidget(self._chk_resolved)

        toolbar.addStretch()

        self._count_label = QLabel("0 active alerts")
        self._count_label.setObjectName("status_text")
        toolbar.addWidget(self._count_label)
        
        layout.addLayout(toolbar)

        # ---- Scrollable Feed ----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self._feed_container = QWidget()
        self._feed_layout = QVBoxLayout(self._feed_container)
        self._feed_layout.setContentsMargins(0, 0, 16, 0) # Right margin for scrollbar
        self._feed_layout.setSpacing(12)
        self._feed_layout.addStretch() # Push items to the top

        self._scroll.setWidget(self._feed_container)
        layout.addWidget(self._scroll)

    def _render_feed(self) -> None:
        """Clear layout and re-populate with current data and filters."""
        # Remove all widgets except the stretch at the end
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        show_resolved = self._chk_resolved.isChecked()
        
        active_count = 0
        for alert in self._alerts_data:
            is_resolved = alert.get("resolved", False)
            if not is_resolved:
                active_count += 1
                
            if is_resolved and not show_resolved:
                continue
                
            widget = AlertItemWidget(alert, self._resolve_alert)
            # Insert before the stretch
            self._feed_layout.insertWidget(self._feed_layout.count() - 1, widget)
            
        self._count_label.setText(f"{active_count} active alert{'s' if active_count != 1 else ''}")

    def _resolve_alert(self, alert_id: int) -> None:
        """Called when a user clicks 'Resolve' on an AlertItemWidget."""
        try:
            self._service.resolve_alert(alert_id)
            # Instantly refresh feed to show it as resolved
            self._manual_refresh()
        except Exception as exc:
            logger.error("Failed to resolve alert %d: %s", alert_id, exc)

    # ------------------------------------------------------------------ #
    # Background worker                                                    #
    # ------------------------------------------------------------------ #

    def _start_worker(self) -> None:
        self._worker = AlertPollWorker()
        self._thread = QThread(self)

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_polling)
        self._thread.finished.connect(self._worker.deleteLater)

        self._worker.metrics_received.connect(self._on_alerts)
        self._worker.error_occurred.connect(self._on_error)

        if self._on_connection_changed is not None:
            self._worker.connection_changed.connect(self._on_connection_changed)

        self._thread.start()
        logger.info("AlertsPage: poll worker thread started")

    def stop_worker(self) -> None:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self._worker, "stop", Qt.ConnectionType.BlockingQueuedConnection
        )
        self._thread.quit()
        self._thread.wait()

    def pause_polling(self) -> None:
        """Temporarily pause the alert feed refresh (e.g., while a dialog is open)."""
        from PySide6.QtCore import QMetaObject, Qt as QtNS
        QMetaObject.invokeMethod(self._worker, "stop", QtNS.ConnectionType.QueuedConnection)
        logger.debug("Alert polling paused")

    def resume_polling(self) -> None:
        """Resume alert feed refresh after a pause."""
        from PySide6.QtCore import QMetaObject, Qt as QtNS
        QMetaObject.invokeMethod(self._worker, "start_polling", QtNS.ConnectionType.QueuedConnection)
        logger.debug("Alert polling resumed")

    def _manual_refresh(self) -> None:
        from PySide6.QtCore import QMetaObject, Qt as QtNS
        QMetaObject.invokeMethod(self._worker, "_fetch", QtNS.ConnectionType.QueuedConnection)

    @Slot(list)
    def _on_alerts(self, data: List[Dict[str, Any]]) -> None:
        self._alerts_data = data
        self._render_feed()

    @Slot(str)
    def _on_error(self, message: str) -> None:
        logger.warning("Alerts poll error: %s", message)
        self._count_label.setText("Backend unreachable")
