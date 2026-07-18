"""
Execution Engine — Node System (Indie Pixel Style)
"""

import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem

# ── Pixel-art palette ──────────────────────────────────────────────
# Each tier of the OS has a distinct palette
TIER_COLORS = {
    "app":      "#38bdf8",   # Cyan — Userspace
    "runtime":  "#818cf8",   # Indigo — Runtimes
    "kernel":   "#c084fc",   # Purple — Kernel
    "hardware": "#34d399",   # Green — Hardware
    "network":  "#60a5fa",   # Blue — Network stack
    "external": "#f87171",   # Red — External / Cloud
    "storage":  "#fbbf24",   # Amber — Storage
}

# Pixel icon glyphs (5x5 bitmap style, drawn as small rects)
_ICONS = {
    "cpu":       "⬡",
    "gpu":       "◈",
    "ram":       "▦",
    "ssd":       "▤",
    "nic":       "◎",
    "scheduler": "⚙",
    "vfs":       "🗂",
    "tcp":       "⇄",
    "firewall":  "🛡",
    "dns":       "◉",
    "internet":  "☁",
    "process":   "▶",
    "container": "⬢",
    "database":  "⛁",
    "cache":     "⟐",
    "swap":      "⇅",
    "iommu":     "⊞",
    "mmu":       "⊡",
    "socket":    "⏣",
    "pipe":      "⟿",
    "default":   "■",
}


class NodeItem(QGraphicsObject):
    """
    A single OS subsystem node rendered in blocky pixel-art style.
    """
    def __init__(self, node_id: str, label: str, color: str = "#3b82f6",
                 icon: str = "default", tier: str = "", parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.label = label
        self.base_color = QColor(color)
        self.icon = _ICONS.get(icon, _ICONS["default"])
        self.tier = tier

        # Pixel-art dimensions (blocky, no rounding)
        self.width = 100
        self.height = 52
        self.border = 3  # Thick pixel border

        # State
        self.load = 0.0  # 0.0 to 1.0
        self.hovered = False
        self._pulse_phase = 0.0
        self._highlight_color = None  # QColor when visited in a journey

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setToolTip(f"{label} ({node_id})")

    def boundingRect(self) -> QRectF:
        margin = 14
        return QRectF(-self.width / 2 - margin, -self.height / 2 - margin,
                      self.width + margin * 2, self.height + margin * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        # Deliberately disable antialiasing for pixel-art crispness
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

        # ── 0. Journey highlight ring ──
        if self._highlight_color is not None:
            ring = QColor(self._highlight_color)
            ring.setAlphaF(0.5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(ring, 4))
            painter.drawRect(rect.adjusted(-9, -9, 9, 9))
            # Inner glow fill
            ring.setAlphaF(0.12)
            painter.setBrush(QBrush(ring))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect.adjusted(-8, -8, 8, 8))

        # ── 1. Outer glow (pulsing with load) ──
        if self.load > 0.3 or self.hovered:
            intensity = min(1.0, self.load * 2.0) if not self.hovered else 0.8
            glow = QColor(self.base_color)
            glow.setAlphaF(0.25 * intensity)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect.adjusted(-5, -5, 5, 5))

        # ── 2. Body fill ──
        body_color = QColor(self.base_color)
        if self.load > 0.8:
            # Overload: flash between base and red
            if int(self._pulse_phase * 4) % 2 == 0:
                body_color = QColor("#ef4444")
        body_color_dark = QColor(body_color)
        body_color_dark.setAlphaF(0.85)

        painter.setBrush(QBrush(body_color_dark))

        # Thick pixel border
        border_color = QColor("#ffffff") if self.hovered else body_color.lighter(160)
        painter.setPen(QPen(border_color, self.border))
        painter.drawRect(rect)

        # ── 3. Inner dark strip (scanline aesthetic) ──
        strip = QRectF(rect.left() + self.border, rect.top() + self.border,
                       rect.width() - self.border * 2, 4)
        painter.setBrush(QBrush(body_color.darker(140)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(strip)

        # ── 4. Icon (top-left pixel badge) ──
        painter.setPen(QColor("#ffffff"))
        icon_font = QFont("monospace", 14)
        painter.setFont(icon_font)
        painter.drawText(QPointF(rect.left() + 6, rect.top() + 20), self.icon)

        # ── 5. Label text ──
        painter.setPen(QColor("#ffffff"))
        label_font = QFont("Courier", 9)
        label_font.setBold(True)
        painter.setFont(label_font)
        label_rect = QRectF(rect.left(), rect.top() + 22, rect.width(), rect.height() - 22)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self.label)

        # ── 6. Tiny load bar along the bottom ──
        if self.load > 0.01:
            bar_y = rect.bottom() - 5
            bar_w = (rect.width() - self.border * 2) * self.load
            bar_color = QColor("#34d399") if self.load < 0.6 else (
                QColor("#fbbf24") if self.load < 0.85 else QColor("#ef4444"))
            painter.setBrush(QBrush(bar_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(rect.left() + self.border, bar_y, bar_w, 4))

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def highlight_visited(self, color: QColor):
        """Mark this node as visited in an execution journey."""
        self._highlight_color = QColor(color) if color else None
        self.update()

    def clear_highlight(self):
        """Remove journey highlight."""
        self._highlight_color = None
        self.update()

    def update_physics(self, dt: float):
        self._pulse_phase += dt
        if self._pulse_phase > 100.0:
            self._pulse_phase = 0.0

        if self.load > 0:
            self.load = max(0.0, self.load - (dt * 0.3))
            self.update()
