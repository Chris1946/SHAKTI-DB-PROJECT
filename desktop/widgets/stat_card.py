"""
PulseTrace Desktop — StatCard Widget (v5 - Futuristic Minimal)
===============================================================

Premium metric card with accent left-border stripe, subtle drop
shadow on hover, and large high-contrast typography.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.ui.theme import Theme

def _bar_colour(value: float) -> str:
    if value <= 60:
        return Theme.get_color("accent_ok")
    if value <= 85:
        return Theme.get_color("accent_warn")
    return Theme.get_color("accent_err")


class StatCard(QFrame):
    """
    Metric display card with accent left-border stripe and hover shadow.
    """

    def __init__(
        self,
        label: str,
        icon: str = "▣",
        accent: str = "#007aff",
        unit: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._unit = unit
        self._build_ui(label, icon)
        Theme.theme_changed.connect(self._apply_style)

    def _apply_style(self) -> None:
        """Apply base styling for the card."""
        bg = Theme.get_color("bg_surface")
        border = Theme.get_color("border")
        text_primary = Theme.get_color("text_primary")
        
        self.setStyleSheet(f"""
            QFrame#stat_card {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame#stat_card:hover {{
                border: 1px solid {self._accent};
            }}
        """)
        if hasattr(self, "_title"):
            self._title.setStyleSheet(f"color: {text_primary}; font-weight: 700; font-size: 15px;")
        if hasattr(self, "_value_label"):
            self._value_label.setStyleSheet(f"color: {text_primary};")
        if hasattr(self, "_sub_label"):
            self._sub_label.setStyleSheet(f"color: {Theme.get_color('text_secondary')};")
        if hasattr(self, "icon_lbl"):
            self.icon_lbl.setStyleSheet(f"color: {Theme.get_color('text_muted')};")

    def _build_ui(self, label: str, icon: str) -> None:
        self.setObjectName("stat_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Drop shadow (subtle, always present, intensifies conceptually on hover)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 12))  # Very subtle
        self.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(0)

        # ── Header: label + icon ──
        header = QHBoxLayout()
        header.setSpacing(0)

        self._title = QLabel(label)
        lbl_font = QFont()
        lbl_font.setPointSize(11)
        lbl_font.setWeight(QFont.Weight.Bold)
        self._title.setFont(lbl_font)

        self.icon_lbl = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(18)
        self.icon_lbl.setFont(icon_font)
        self.icon_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self.icon_lbl)
        outer.addLayout(header)

        outer.addSpacing(12)

        # ── Large value ──
        self._value_label = QLabel("—")
        val_font = QFont()
        val_font.setPointSize(34)
        val_font.setWeight(QFont.Weight.Bold)
        self._value_label.setFont(val_font)
        outer.addWidget(self._value_label)

        outer.addSpacing(12)

        # ── Thin progress bar ──
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._set_bar_style(0.0)
        outer.addWidget(self._progress)

        outer.addSpacing(10)

        # ── Sub-label ──
        self._sub_label = QLabel("")
        sub_font = QFont()
        sub_font.setPointSize(12)
        self._sub_label.setFont(sub_font)
        outer.addWidget(self._sub_label)

        outer.addStretch()
        
        self._apply_style()

    # ────────────────────────────────────────────────────────── #
    # Public API                                                  #
    # ────────────────────────────────────────────────────────── #

    def update_value(
        self,
        value: float,
        *,
        sub: str = "",
        bar_value: Optional[float] = None,
        raw_label: Optional[str] = None,
    ) -> None:
        """Refresh the displayed metric."""
        if raw_label is not None:
            self._value_label.setText(raw_label)
        else:
            self._value_label.setText(f"{value:.1f}{self._unit}")

        pct = bar_value if bar_value is not None else value
        self._set_bar_style(pct)
        self._progress.setValue(max(0, min(100, int(pct))))

        if sub:
            self._sub_label.setText(sub)

    def _set_bar_style(self, pct: float) -> None:
        color_hex = _bar_colour(pct)
        bg = Theme.get_color("bg_alt")
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {bg};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {color_hex};
                border-radius: 4px;
            }}
        """)
