"""
Execution Engine — Packet Legend Box
Shows a floating legend indicating what each packet color means.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from desktop.ui.theme import Theme

class LegendBox(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LegendBox")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(16)
        
        title = QLabel("LEGEND:")
        title.setStyleSheet(f"color: {Theme.get_color('text_muted')}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(title)
        
        grid = QWidget()
        grid_layout = QHBoxLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(16)
        
        # Define the packet types and their colors
        legend_items = [
            ("#38bdf8", "Network Inbound"),
            ("#818cf8", "Network Outbound"),
            ("#34d399", "Disk Read"),
            ("#fbbf24", "Disk Write"),
            ("#f87171", "DNS Query"),
            ("#c084fc", "Memory / Context Switch"),
            ("#14b8a6", "Swap Page-Out"),
            ("#f472b6", "DB Query"),
            ("#06b6d4", "Container Exec"),
            ("#a3e635", "GPU Compute")
        ]
        
        for color, label_text in legend_items:
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            color_box = QFrame()
            color_box.setFixedSize(10, 10)
            color_box.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
            
            label = QLabel(label_text)
            label.setStyleSheet(f"color: {Theme.get_color('text_primary')}; font-size: 10px;")
            
            item_layout.addWidget(color_box)
            item_layout.addWidget(label)
            
            grid_layout.addLayout(item_layout)
            
        grid_layout.addStretch()
        layout.addWidget(grid)
        layout.addStretch()
            
        self._apply_theme()
        Theme.theme_changed.connect(self._apply_theme)
        
    def _apply_theme(self):
        bg = Theme.get_color("bg_surface")
        border = Theme.get_color("border")
        self.setStyleSheet(f"""
            QFrame#LegendBox {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)
