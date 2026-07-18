"""
PulseTrace Desktop — TimeSeries Widget
========================================

A high-performance real-time line chart built on ``pyqtgraph``.

  ┌──────────────────────────────────────────────────────────────────┐
  │  CPU %   ─────────────────────────────────────────────────────   │  (gold)
  │  MEM %   ─────────────────────────────────────────────────────   │  (violet)
  │                                                                   │
  │  100% ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
  │   75% ─                                                           │
  │   50% ─                        ╭───╮                             │
  │   25% ─                  ╭─────╯   ╰─────────                   │
  │    0% ─ ─ ─ ─ ─ ─ ─ ─ ─ ╯                                       │
  │                                                                   │
  │  ◀──────────────────── last 5 minutes ──────────────────────▶   │
  └──────────────────────────────────────────────────────────────────┘

Design goals
------------
- Maximum rendering performance: pyqtgraph OpenGL/numpy path.
- Rolling window: holds the last ``max_points`` samples.
- Multiple series: add as many lines as needed via ``add_series()``.
- No pandas dependency: uses plain Python collections.

Usage
-----
    chart = TimeSeriesWidget(title="System Load", max_points=120)
    cpu_line = chart.add_series("CPU %",    colour="#3b82f6")
    mem_line = chart.add_series("Memory %", colour="#8b5cf6")

    # On each poll tick:
    chart.push(cpu_line, cpu_value)
    chart.push(mem_line, mem_value)
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple

import pyqtgraph as pg
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QWidget

from desktop.ui.theme import Theme

# pyqtgraph global config — MUST match theme (light)
pg.setConfigOptions(antialias=True, foreground="#6b7280", background="#ffffff")


class _Series:
    """Internal holder for a single data series."""

    def __init__(self, name: str, colour: str, max_points: int) -> None:
        self.name = name
        self.colour = colour
        self.data: deque[float] = deque([0.0] * max_points, maxlen=max_points)
        self.curve: Optional[pg.PlotDataItem] = None
        self.label: Optional[QLabel] = None


class TimeSeriesWidget(QWidget):
    """
    A rolling time-series chart powered by pyqtgraph.

    Parameters
    ----------
    title:       Optional text shown above the plot area.
    max_points:  How many samples to keep in the rolling window.
                 At 5-second intervals, 120 points = 10 minutes.
    y_min/y_max: Fixed Y-axis range (default 0–100 for percentages).
    parent:      Standard Qt parent.
    """

    def __init__(
        self,
        title: str = "",
        max_points: int = 120,
        y_min: float = 0.0,
        y_max: float = 100.0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._max_points = max_points
        self._series: Dict[int, _Series] = {}
        self._next_id = 0
        self._build_ui(title, y_min, y_max)
        Theme.theme_changed.connect(self._apply_theme)

    # ------------------------------------------------------------------ #
    # Construction                                                         #
    # ------------------------------------------------------------------ #

    def _build_ui(self, title: str, y_min: float, y_max: float) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._stats_layout = QHBoxLayout()
        self._stats_layout.setContentsMargins(12, 8, 12, 0)
        layout.addLayout(self._stats_layout)

        self._plot = pg.PlotWidget(title=title)
        self._plot.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Grid lines — very subtle light grey
        self._plot.showGrid(x=True, y=True, alpha=0.15)

        # ---- Visual config ----
        plot_item = self._plot.getPlotItem()

        # Fixed ranges — no auto-scroll
        self._plot.setYRange(y_min, y_max, padding=0.05)
        self._plot.setXRange(0, self._max_points - 1, padding=0)

        # Pure display widget — no mouse interaction
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.setMenuEnabled(False)

        plot_item.setContentsMargins(0, 4, 0, 0)

        layout.addWidget(self._plot)
        self._apply_theme()
        
    def _apply_theme(self) -> None:
        bg = Theme.get_color("bg_surface")
        text = Theme.get_color("text_muted")
        grid = Theme.get_color("border")
        
        self._plot.setBackground(bg)
        plot_item = self._plot.getPlotItem()
        left_axis = plot_item.getAxis("left")
        bottom_axis = plot_item.getAxis("bottom")
        
        left_axis.setStyle(tickFont=pg.QtGui.QFont("SF Pro Text", 9))
        bottom_axis.setStyle(showValues=False)
        left_axis.setTextPen(text)
        bottom_axis.setTextPen(text)
        left_axis.setPen(pg.mkPen(grid, width=1))
        bottom_axis.setPen(pg.mkPen(grid, width=1))

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def add_series(self, name: str, colour: str = "#6366f1") -> int:
        """
        Register a new data series.

        Returns an integer handle used to push data and remove the series.
        """
        series = _Series(name, colour, self._max_points)

        pen = pg.mkPen(colour, width=2.5)
        # Soft fill under the line
        fill_color = QColor(colour)
        fill_color.setAlphaF(0.12)
        brush = pg.mkBrush(fill_color)

        series.curve = self._plot.plot(
            list(series.data),
            name=name,
            pen=pen,
            fillLevel=0,
            brush=brush,
        )

        lbl = QLabel(f"{name}: -")
        lbl.setStyleSheet(f"color: {colour}; font-weight: bold; font-size: 11px;")
        self._stats_layout.addWidget(lbl)
        series.label = lbl
        self._stats_layout.addStretch()

        handle = self._next_id
        self._series[handle] = series
        self._next_id += 1
        return handle

    def push(self, series_id: int, value: float) -> None:
        """
        Append a new data point to the rolling window and refresh the curve.

        Parameters
        ----------
        series_id:  Handle returned by ``add_series()``.
        value:      New metric value to append.
        """
        if series_id not in self._series:
            return
        s = self._series[series_id]
        s.data.append(value)
        if s.curve is not None:
            s.curve.setData(list(s.data))
            
        if s.label is not None:
            avg = sum(s.data) / len(s.data) if s.data else 0.0
            
            def fmt(v: float) -> str:
                if v > 1000000: return f"{v/1000000:.1f}M"
                if v > 1000: return f"{v/1000:.1f}K"
                return f"{v:.1f}"
                
            s.label.setText(f"{s.name}: {fmt(value)} (Avg: {fmt(avg)})")

    def clear_series(self, series_id: int) -> None:
        """Reset a series' data to zeros without removing it from the chart."""
        if series_id not in self._series:
            return
        s = self._series[series_id]
        s.data = deque([0.0] * self._max_points, maxlen=self._max_points)
        if s.curve is not None:
            s.curve.setData(list(s.data))
