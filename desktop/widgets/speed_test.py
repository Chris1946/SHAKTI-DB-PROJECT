"""
Speed Test Widget
Provides a circular gauge for testing network speed via speedtest-cli.
"""

import math
from PySide6.QtCore import Qt, QRectF, QThread, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
import speedtest
import logging
from desktop.ui.theme import Theme

logger = logging.getLogger(__name__)


class SpeedTestWorker(QThread):
    progress = Signal(str, float, float)  # phase, value, max_value
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            self.progress.emit("Finding Server...", 0, 100)
            try:
                st = speedtest.Speedtest(secure=True)
                b = st.get_best_server()
                
                self.progress.emit("Testing Ping...", 50, 100)
                ping_val = b.get("latency", 0)
                if ping_val >= 10000:
                    host = b.get("host", "").split(":")[0]
                    import subprocess
                    import re
                    try:
                        out = subprocess.check_output(f"ping -c 1 {host}", shell=True, timeout=2).decode()
                        match = re.search(r"time=([\d\.]+)", out)
                        if match:
                            ping_val = float(match.group(1))
                    except Exception:
                        ping_val = 0
                        
                results = {"ping": ping_val}
                
                # Download test
                self.progress.emit("Download", 0, 100)
                self.progress.emit("Download", 50, 100)
                dl = st.download()
                results["download"] = dl / 1_000_000  # Mbps
                self.progress.emit("Download", 100, 100)
                
                # Upload test
                self.progress.emit("Upload", 0, 100)
                self.progress.emit("Upload", 50, 100)
                ul = st.upload()
                results["upload"] = ul / 1_000_000  # Mbps
                self.progress.emit("Upload", 100, 100)
                
                self.finished.emit(results)
                
            except speedtest.ConfigRetrievalError:
                self._run_cloudflare_fallback()
                
        except Exception as e:
            logger.error(f"Speedtest error: {e}", exc_info=True)
            self.error.emit(str(e))

    def _run_cloudflare_fallback(self):
        import urllib.request
        import time
        import os
        import subprocess, re
        
        self.progress.emit("Bypassing Firewall...", 50, 100)
        ping_val = 0
        try:
            out = subprocess.check_output("ping -c 1 speedtest.tele2.net", shell=True, timeout=2).decode()
            match = re.search(r"time=([\d\.]+)", out)
            if match:
                ping_val = float(match.group(1))
        except Exception:
            pass
            
        self.progress.emit("Fallback Down", 50, 100)
        req = urllib.request.Request("http://speedtest.tele2.net/10MB.zip")
        start = time.time()
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()
            dur = max(0.001, time.time() - start)
            dl_mbps = (len(data) * 8 / 1_000_000) / dur
        except Exception:
            dl_mbps = 0.0
        
        self.progress.emit("Fallback Up", 50, 100)
        req_up = urllib.request.Request("http://speedtest.tele2.net/upload.php", data=os.urandom(5_000_000), method="POST")
        start = time.time()
        try:
            urllib.request.urlopen(req_up, timeout=10)
        except Exception:
            pass # timeout is ok, we just measure how long the upload took before socket closed
        dur = max(0.001, time.time() - start)
        ul_mbps = (5_000_000 * 8 / 1_000_000) / dur
        
        self.finished.emit({
            "ping": ping_val,
            "download": dl_mbps,
            "upload": ul_mbps
        })


class CircularGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.value = 0
        self.max_value = 100
        self.label = "Ready"
        self.color = QColor(Theme.get_color("accent_primary"))
        
    def set_state(self, label: str, val: float, mx: float = 100, color: str = None):
        self.label = label
        self.value = val
        self.max_value = mx
        if color:
            self.color = QColor(color)
        else:
            self.color = QColor(Theme.get_color("accent_primary"))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(15, 15, self.width() - 30, self.height() - 30)
        
        # Background arc
        pen_bg = QPen(QColor(Theme.get_color("border")), 12)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        # Start at 210 degrees (bottom left), span -240 (clockwise to bottom right)
        painter.drawArc(rect, 16 * 210, 16 * -240)
        
        # Value arc
        ratio = min(1.0, max(0.0, self.value / self.max_value if self.max_value > 0 else 0))
        span_angle = 16 * -240 * ratio
        
        if span_angle != 0:
            pen_val = QPen(self.color, 12)
            pen_val.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_val)
            painter.drawArc(rect, 16 * 210, span_angle)
            
        # Draw value text
        painter.setPen(QColor(Theme.get_color("text_primary")))
        font_val = QFont("SF Pro Text", 20, QFont.Weight.Bold)
        painter.setFont(font_val)
        val_rect = QRectF(rect.x(), rect.y() - 10, rect.width(), rect.height())
        painter.drawText(val_rect, Qt.AlignmentFlag.AlignCenter, f"{self.value:.1f}")
        
        # Draw label text
        painter.setPen(QColor(Theme.get_color("text_muted")))
        font_lbl = QFont("SF Pro Text", 10, QFont.Weight.Medium)
        painter.setFont(font_lbl)
        lbl_rect = QRectF(rect.x(), rect.y() + 25, rect.width(), rect.height())
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, self.label)


class SpeedTestWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("speedtest_panel")
        self.setStyleSheet(f"""
            QWidget#speedtest_panel {{
                background-color: {Theme.get_color('bg_surface')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 8px;
            }}
        """)
        
        self._build_ui()
        self._worker = None

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Network Speed Test")
        title_font = QFont("SF Pro Text", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {Theme.get_color('text_primary')};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Gauge
        gauge_layout = QHBoxLayout()
        self.gauge = CircularGauge()
        gauge_layout.addStretch()
        gauge_layout.addWidget(self.gauge)
        gauge_layout.addStretch()
        main_layout.addLayout(gauge_layout)
        
        # Results area
        results_layout = QHBoxLayout()
        self.lbl_ping = self._make_stat_lbl("Ping", "-- ms")
        self.lbl_down = self._make_stat_lbl("Down", "-- Mbps")
        self.lbl_up = self._make_stat_lbl("Up", "-- Mbps")
        
        results_layout.addWidget(self.lbl_ping)
        results_layout.addWidget(self.lbl_down)
        results_layout.addWidget(self.lbl_up)
        main_layout.addLayout(results_layout)
        
        # Action button
        self.btn_start = QPushButton("START TEST")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.get_color('accent_primary')};
                color: white;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Theme.get_color('accent_hover')};
            }}
            QPushButton:disabled {{
                background-color: {Theme.get_color('border')};
                color: {Theme.get_color('text_muted')};
            }}
        """)
        self.btn_start.clicked.connect(self.start_test)
        main_layout.addWidget(self.btn_start)
        
    def _make_stat_lbl(self, title, val):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0,0,0,0)
        t = QLabel(title)
        t.setStyleSheet(f"color: {Theme.get_color('text_muted')}; font-size: 10px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v = QLabel(val)
        v.setStyleSheet(f"color: {Theme.get_color('text_primary')}; font-weight: bold;")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t)
        l.addWidget(v)
        w.val_lbl = v
        return w

    def start_test(self):
        self.btn_start.setEnabled(False)
        self.lbl_ping.val_lbl.setText("-- ms")
        self.lbl_down.val_lbl.setText("-- Mbps")
        self.lbl_up.val_lbl.setText("-- Mbps")
        self.gauge.set_state("Initializing...", 0, 100)
        
        self._worker = SpeedTestWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, phase, val, mx):
        color = Theme.get_color("accent_primary")
        if phase == "Upload":
            color = Theme.get_color("accent_warn")
        elif phase == "Download":
            color = Theme.get_color("accent_ok")
            
        self.gauge.set_state(phase, val, mx, color)

    def _on_finished(self, results):
        ping = results.get("ping", 0)
        down = results.get("download", 0)
        up = results.get("upload", 0)
        
        self.lbl_ping.val_lbl.setText(f"{ping:.0f} ms")
        self.lbl_down.val_lbl.setText(f"{down:.1f} Mbps")
        self.lbl_up.val_lbl.setText(f"{up:.1f} Mbps")
        
        max_val = max(100.0, down, up)
        self.gauge.set_state("Complete", down, max_val, Theme.get_color("accent_ok"))
        self.btn_start.setEnabled(True)

    def _on_error(self, err):
        logger.error(f"SpeedTest GUI error received: {err}")
        if "Errno 54" in err or "Connection reset" in err or "ConfigRetrievalError" in err:
            self.gauge.set_state("Server Rate Limited", 0, 100, Theme.get_color("accent_warn"))
            self.lbl_ping.val_lbl.setText("Rate")
            self.lbl_down.val_lbl.setText("Limited")
            self.lbl_up.val_lbl.setText("---")
        else:
            self.gauge.set_state("Error", 0, 100, Theme.get_color("accent_crit"))
            self.lbl_ping.val_lbl.setText("Err")
            self.lbl_down.val_lbl.setText("Err")
            self.lbl_up.val_lbl.setText("Err")
        self.btn_start.setEnabled(True)
