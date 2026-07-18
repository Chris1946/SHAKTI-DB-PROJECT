"""
PulseTrace Execution Engine Framework
White background, zoom buttons, pinch/scroll zoom, 60fps game loop.
"""

from typing import List
from PySide6.QtCore import Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent, QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QFrame,
)

from desktop.ui.theme import Theme


class TimeManager:
    """Controls simulation time."""
    def __init__(self):
        self.multiplier = 1.0
        self.paused = False
        self.time_elapsed = 0.0

    def tick(self, dt: float) -> float:
        if self.paused:
            return 0.0
        scaled_dt = dt * self.multiplier
        self.time_elapsed += scaled_dt
        return scaled_dt


ZOOM_MIN = 0.3
ZOOM_MAX = 3.0
ZOOM_STEP = 1.25


class ExecutionEngine(QGraphicsView):
    """
    The main 2D renderer. White background, zoom buttons, scroll zoom.
    """
    item_inspected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)

        # Rendering
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self._hovered_item = None

        self.time_manager = TimeManager()
        self.followed_item: QGraphicsItem = None
        self.active_entities = []

        # 60 FPS game loop
        self.fps = 60
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._game_loop)
        self._timer.start(int(1000 / self.fps))

        self._zoom = 1.0

        # ── Zoom buttons (overlay) ──
        self._setup_zoom_buttons()
        self._apply_theme()
        Theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        bg = Theme.get_color("bg_base")
        self.scene_obj.setBackgroundBrush(QBrush(QColor(bg)))
        self.setStyleSheet(f"QGraphicsView {{ border: none; }}")
        
        btn_css = f"""
            QPushButton {{
                background: {Theme.get_color('bg_surface')};
                color: {Theme.get_color('text_primary')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
                font-family: monospace;
            }}
            QPushButton:hover {{ background: {Theme.get_color('bg_alt')}; }}
            QPushButton:pressed {{ background: {Theme.get_color('border')}; }}
        """
        for btn in (self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_fit):
            btn.setStyleSheet(btn_css)
            
        self.viewport().update()

    def _setup_zoom_buttons(self):
        """Create +/- zoom buttons overlaid on the top-right corner."""
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_fit = QPushButton("⊡")

        for btn in (self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_fit):
            btn.setParent(self)
            btn.setFixedSize(32, 32)

        self.btn_zoom_in.setToolTip("Zoom In")
        self.btn_zoom_out.setToolTip("Zoom Out")
        self.btn_zoom_fit.setToolTip("Fit to View")

        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_fit.clicked.connect(self.zoom_reset)

    def resizeEvent(self, event):
        """Reposition zoom buttons when view resizes."""
        super().resizeEvent(event)
        x = self.width() - 42
        self.btn_zoom_in.move(x, 10)
        self.btn_zoom_out.move(x, 46)
        self.btn_zoom_fit.move(x, 82)

    def add_item(self, item: QGraphicsItem):
        self.scene_obj.addItem(item)
        if hasattr(item, "update_physics"):
            self.active_entities.append(item)

    def drawBackground(self, painter: QPainter, rect):
        """Subtle dot grid on background."""
        super().drawBackground(painter, rect)
        grid_size = 40
        pen = QPen(QColor(Theme.get_color("divider")), 2)
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(x, y)
                y += grid_size
            x += grid_size

    def _game_loop(self):
        base_dt = 1.0 / self.fps
        dt = self.time_manager.tick(base_dt)

        if dt > 0:
            dead = []
            for item in self.active_entities:
                if item.scene():
                    item.update_physics(dt)
                else:
                    dead.append(item)
            
            for item in dead:
                self.active_entities.remove(item)

        if self.followed_item and self.followed_item.scene():
            self.centerOn(self.followed_item)

    # ── Zoom methods ──────────────────────────────────────────

    def _apply_zoom(self, new_zoom: float):
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
        factor = new_zoom / self._zoom
        self._zoom = new_zoom
        self.scale(factor, factor)

    def zoom_in(self):
        self._apply_zoom(self._zoom * ZOOM_STEP)

    def zoom_out(self):
        self._apply_zoom(self._zoom / ZOOM_STEP)

    def zoom_reset(self):
        """Reset view to default zoom."""
        self.resetTransform()
        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent):
        """Scroll/pinch to zoom."""
        if event.angleDelta().y() > 0:
            self._apply_zoom(self._zoom * ZOOM_STEP)
        else:
            self._apply_zoom(self._zoom / ZOOM_STEP)

    # ── Mouse interaction ─────────────────────────────────────
    
    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item:
            while item.parentItem():
                item = item.parentItem()
            if item != self._hovered_item:
                self._hovered_item = item
                self.item_inspected.emit(item)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.followed_item = None
            item = self.itemAt(event.pos())
            if item:
                while item.parentItem():
                    item = item.parentItem()
                self.item_inspected.emit(item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                while item.parentItem():
                    item = item.parentItem()
                self.followed_item = item
        super().mouseDoubleClickEvent(event)
