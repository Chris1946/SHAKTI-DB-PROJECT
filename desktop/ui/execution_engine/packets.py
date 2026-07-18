"""
Execution Engine — Packet System (Indie Pixel Style)
Packets show a hover tooltip with key metadata.
"""

from typing import Dict, Any, List
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QToolTip

from desktop.ui.execution_engine.nodes import NodeItem

# Keys to show in hover tooltip, in order
_TOOLTIP_KEYS = [
    ("type",      "Type"),
    ("protocol",  "Proto"),
    ("src_ip",    "Src"),
    ("src_port",  "SrcPort"),
    ("dst_ip",    "Dst"),
    ("dst_port",  "DstPort"),
    ("process",   "Proc"),
    ("size",      "Size"),
    ("direction", "Dir"),
    ("operation", "Op"),
    ("syscall",   "Call"),
    ("engine",    "DB"),
]

_HIDDEN_KEYS = {"color", "speed", "path", "confidence"}


class PacketItem(QGraphicsObject):
    """
    A data packet that travels along edges between nodes.
    Rendered as a pixel-art diamond/square with a glowing trail.
    Shows metadata tooltip on hover.
    """
    def __init__(self, metadata: Dict[str, Any], path_nodes: List[NodeItem], parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.path_nodes = path_nodes

        # State
        self.current_index = 0
        self.progress = 0.0
        self.speed = metadata.get("speed", 0.4)
        self.color = QColor(metadata.get("color", "#38bdf8"))

        self.size = 7  # Half-width of diamond
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable)

        # Traversal tracking for journey view
        self.traversal_log = []
        self._journey_time = 0.0

        # Build tooltip text once
        self._build_tooltip()

        # Initialize position
        if self.path_nodes:
            self.setPos(self.path_nodes[0].pos())
            self.path_nodes[0].load = min(1.0, self.path_nodes[0].load + 0.08)
            # Log the first node
            self.traversal_log.append({"node": self.path_nodes[0].label, "time": 0.0})
            self.path_nodes[0].highlight_visited(self.color)

    def _build_tooltip(self):
        """Build a rich text tooltip from metadata."""
        lines = []
        shown = set()
        for key, label in _TOOLTIP_KEYS:
            if key in self.metadata:
                val = self.metadata[key]
                lines.append(f"<b>{label}:</b> {val}")
                shown.add(key)
        # Any extra keys
        for key, val in self.metadata.items():
            if key not in shown and key not in _HIDDEN_KEYS:
                lines.append(f"<b>{key}:</b> {val}")

        # Journey
        if self.path_nodes:
            path_str = " → ".join(n.label for n in self.path_nodes)
            lines.append(f"<b>Path:</b> {path_str}")

        tooltip_html = "<br/>".join(lines)
        self.setToolTip(
            f"<div style='font-family:Courier; font-size:11px; color:#e2e8f0; "
            f"background:#1e293b; padding:6px; border:2px solid {self.color.name()};'>"
            f"{tooltip_html}</div>"
        )

    def boundingRect(self) -> QRectF:
        margin = 12
        return QRectF(-self.size - margin, -self.size - margin,
                      self.size * 2 + margin * 2, self.size * 2 + margin * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        s = self.size

        # ── Glow square behind ──
        glow = QColor(self.color)
        glow.setAlphaF(0.3)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(-s - 4, -s - 4, (s + 4) * 2, (s + 4) * 2))

        # ── Diamond shape (rotated square) ──
        # Drawn as a polygon for pixel crispness
        from PySide6.QtGui import QPolygonF
        diamond = QPolygonF([
            QPointF(0, -s),
            QPointF(s, 0),
            QPointF(0, s),
            QPointF(-s, 0),
        ])
        painter.setBrush(QBrush(self.color))
        border_color = QColor("#ffffff") if self.isSelected() else self.color.lighter(140)
        painter.setPen(QPen(border_color, 2))
        painter.drawPolygon(diamond)

        # ── Tiny direction arrow in center ──
        painter.setPen(QColor("#0f172a"))
        font = QFont("Courier", 7)
        font.setBold(True)
        painter.setFont(font)
        direction = self.metadata.get("direction", "")
        glyph = "→" if direction == "OUTBOUND" else ("←" if direction == "INBOUND" else "·")
        painter.drawText(QRectF(-s, -s, s * 2, s * 2), Qt.AlignmentFlag.AlignCenter, glyph)

    def hoverEnterEvent(self, event):
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.update()
        super().hoverLeaveEvent(event)

    def update_physics(self, dt: float):
        if self.current_index >= len(self.path_nodes) - 1:
            if self.scene():
                self.scene().removeItem(self)
            return

        self._journey_time += dt
        self.progress += dt * self.speed

        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_index += 1
            if self.current_index < len(self.path_nodes):
                node = self.path_nodes[self.current_index]
                node.load = min(1.0, node.load + 0.08)
                # Track traversal and highlight visited node
                self.traversal_log.append({"node": node.label, "time": self._journey_time})
                node.highlight_visited(self.color)

        if self.current_index < len(self.path_nodes) - 1:
            p1 = self.path_nodes[self.current_index].pos()
            p2 = self.path_nodes[self.current_index + 1].pos()

            # Follow bezier path matching edge curves
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            path = QPainterPath(p1)
            path.cubicTo(
                QPointF(p1.x() + dx * 0.4, p1.y() + dy * 0.1),
                QPointF(p2.x() - dx * 0.4, p2.y() - dy * 0.1),
                p2
            )
            self.setPos(path.pointAtPercent(self.progress))
