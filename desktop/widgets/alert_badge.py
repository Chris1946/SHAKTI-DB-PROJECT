"""
PulseTrace Desktop — AlertBadge Widget
========================================

A compact severity pill:

  ● CRITICAL   (red-tinted)
  ● WARNING    (amber-tinted)
  ● INFO       (indigo-tinted)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget


# Severity → (icon, bg, fg, border)
_SEVERITY_STYLES: dict[str, tuple[str, str, str, str]] = {
    "critical": ("●", "rgba(248,113,113,0.12)", "#f87171", "rgba(248,113,113,0.3)"),
    "warning":  ("●", "rgba(251,191,36,0.12)",  "#fbbf24", "rgba(251,191,36,0.3)"),
    "info":     ("●", "rgba(99,102,241,0.12)",  "#818cf8", "rgba(99,102,241,0.3)"),
}
_DEFAULT_STYLE = ("●", "rgba(74,85,104,0.15)", "#4a5568", "rgba(74,85,104,0.3)")


class AlertBadge(QLabel):
    """
    Inline severity pill badge.

    Parameters
    ----------
    severity:  ``"critical"``, ``"warning"``, or ``"info"``.
    """

    def __init__(
        self,
        severity: str = "info",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.set_severity(severity)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.setFont(font)

    def set_severity(self, severity: str) -> None:
        key = severity.lower()
        icon, bg, fg, border = _SEVERITY_STYLES.get(key, _DEFAULT_STYLE)
        self.setText(f"  {icon}  {severity.upper()}  ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.8px;
            }}
        """)
