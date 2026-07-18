"""
Execution Engine — Edge System (Indie Pixel Style)
"""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem

from desktop.ui.execution_engine.nodes import NodeItem


class EdgeItem(QGraphicsPathItem):
    """
    Pixel-style dashed connection line between two nodes.
    """
    def __init__(self, source: NodeItem, target: NodeItem, parent=None):
        super().__init__(parent)
        self.source = source
        self.target = target

        # Style
        self.color = QColor("#334155")
        self.thickness = 2

        self.setZValue(-1)  # Draw behind nodes
        self.update_path()

    def update_path(self):
        if not self.source or not self.target:
            return

        start = self.source.pos()
        end = self.target.pos()

        # Bezier curve with moderate control point offset
        path = QPainterPath(start)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        ctrl1 = QPointF(start.x() + dx * 0.4, start.y() + dy * 0.1)
        ctrl2 = QPointF(end.x() - dx * 0.4, end.y() - dy * 0.1)
        path.cubicTo(ctrl1, ctrl2, end)
        self.setPath(path)

        pen = QPen(self.color, self.thickness)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 4])  # Pixel-style dashes
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        self.setPen(pen)

    def paint(self, painter: QPainter, option, widget=None):
        # No antialiasing for pixel crispness
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        super().paint(painter, option, widget)
