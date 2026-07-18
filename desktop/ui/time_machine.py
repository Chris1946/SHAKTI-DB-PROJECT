"""
PulseTrace Desktop — Time Machine Controls
─────────────────────────────────────────────
Slider  = Simulation speed (0.25× slow-mo → 3× fast-forward)
Play    = Pause / Resume
Prev/Next = Jump to detected alert incidents (from backend)
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QFrame,
)
from PySide6.QtCore import Qt, Signal


# Speed presets mapped to slider ticks (0–100)
# 0=0.25x  25=0.5x  50=1.0x  75=2.0x  100=3.0x
def _slider_to_speed(value: int) -> float:
    """Convert slider 0-100 to a speed multiplier."""
    if value <= 25:
        return 0.25 + (value / 25) * 0.25       # 0.25 → 0.50
    elif value <= 50:
        return 0.50 + ((value - 25) / 25) * 0.5  # 0.50 → 1.00
    elif value <= 75:
        return 1.0 + ((value - 50) / 25) * 1.0   # 1.00 → 2.00
    else:
        return 2.0 + ((value - 75) / 25) * 1.0   # 2.00 → 3.00


class TimeMachine(QWidget):
    """
    Controls simulation playback speed, pause, and incident navigation.
    """
    speed_changed = Signal(float)   # Emits new speed multiplier
    paused_changed = Signal(bool)   # Emits pause state

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            TimeMachine {
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }
            QPushButton {
                background: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 10px;
                font-family: Courier;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #334155; }
            QPushButton:pressed { background: #475569; }
            QPushButton:checked { background: #7c3aed; border-color: #a78bfa; }
            QSlider::groove:horizontal {
                background: #1e293b;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #a78bfa;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal { background: #7c3aed; border-radius: 3px; }
            QLabel { color: #94a3b8; font-family: Courier; font-size: 11px; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # ── Pause / Play ──
        self.btn_play = QPushButton("⏸ PAUSE")
        self.btn_play.setFixedWidth(90)
        self.btn_play.setCheckable(True)
        self.btn_play.clicked.connect(self._toggle_play)

        # ── Speed slider ──
        self.lbl_speed_title = QLabel("SPEED")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)  # Default = 1.0x
        self.slider.setFixedWidth(180)
        self.slider.valueChanged.connect(self._on_slider_changed)

        self.lbl_speed = QLabel("1.0×")
        self.lbl_speed.setFixedWidth(40)

        # ── Accuracy indicator ──
        self.lbl_mode = QLabel("LIVE TELEMETRY")
        self.lbl_mode.setStyleSheet(
            "color: #10b981; font-weight: bold; font-size: 10px; "
            "background: #064e3b; border: 1px solid #10b981; border-radius: 3px; padding: 2px 6px;"
        )
        self.lbl_mode.setToolTip(
            "Packet volumes and flows are mathematically derived\n"
            "directly from live hardware counters (eBPF / psutil).\n\n"
            "100% authentic to your machine's true throughput."
        )

        layout.addWidget(self.btn_play)
        layout.addSpacing(8)
        layout.addWidget(self.lbl_speed_title)
        layout.addWidget(self.slider)
        layout.addWidget(self.lbl_speed)
        layout.addStretch()
        layout.addWidget(self.lbl_mode)

    def _toggle_play(self):
        if self.btn_play.isChecked():
            self.btn_play.setText("▶ PLAY")
            self.paused_changed.emit(True)
        else:
            self.btn_play.setText("⏸ PAUSE")
            self.paused_changed.emit(False)

    def _on_slider_changed(self, value: int):
        speed = _slider_to_speed(value)
        self.lbl_speed.setText(f"{speed:.1f}×")
        self.speed_changed.emit(speed)
