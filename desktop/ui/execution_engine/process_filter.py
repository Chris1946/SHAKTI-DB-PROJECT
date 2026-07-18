"""
Execution Engine — Process Filter Bar
Displays clickable process buttons to filter which packets are visible.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from desktop.ui.theme import Theme


# The simulated process pool (must match simulator._PROCESS_NAMES)
PROCESS_LIST = [
    ("ALL",               None, "#e2e8f0"),
    ("chrome",            4821, "#38bdf8"),
    ("python3",           1923, "#c084fc"),
    ("node",              3417, "#34d399"),
    ("pulsetrace-agent",  2210, "#f472b6"),
    ("sshd",              1101, "#fbbf24"),
    ("nginx",              982, "#fb923c"),
    ("docker",            1560, "#06b6d4"),
    ("postgres",          3901, "#a78bfa"),
    ("redis-server",      4102, "#ef4444"),
    ("containerd",        1245, "#818cf8"),
]


class ProcessFilterBar(QFrame):
    """
    Horizontal bar of clickable process chips.
    Clicking a process filters packets to only show that process's data flows.
    """
    process_selected = Signal(str)  # Emits process name or "ALL"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProcessFilterBar")
        self.setFixedHeight(56)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)

        self.label = QLabel("FILTER BY PROCESS")
        outer.addWidget(self.label)

        # Scrollable chip area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setFixedHeight(40)

        chip_container = QWidget()
        chip_layout = QHBoxLayout(chip_container)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(6)

        self._buttons = {}
        self._active = "ALL"

        for name, pid, color in PROCESS_LIST:
            if pid:
                label_text = f"{name}\nPID {pid}"
            else:
                label_text = name

            btn = QPushButton(label_text)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, n=name: self._on_click(n))
            chip_layout.addWidget(btn)
            # Store tuple of (button, color) so we can reapply stylesheets on theme change
            self._buttons[name] = (btn, color)
            
            if name == "ALL":
                btn.setChecked(True)

        chip_layout.addStretch()
        scroll.setWidget(chip_container)
        outer.addWidget(scroll, stretch=1)
        
        self._apply_theme()
        Theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        bg = Theme.get_color("bg_base")
        border = Theme.get_color("border")
        self.setStyleSheet(f"""
            QFrame#ProcessFilterBar {{
                background: {bg};
                border-top: 1px solid {border};
            }}
        """)
        self.label.setStyleSheet(f"color: {Theme.get_color('text_muted')}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        
        for name, (btn, color) in self._buttons.items():
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Theme.get_color('bg_surface')};
                    color: {Theme.get_color('text_primary')};
                    border: 1px solid {Theme.get_color('border')};
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ 
                    background: {Theme.get_color('bg_alt')}; 
                    border: 1px solid {color};
                    color: {color};
                }}
                QPushButton:checked {{
                    background: {color};
                    color: #ffffff;
                    border-color: {color};
                    font-weight: 700;
                }}
            """)

    def _on_click(self, name: str):
        self._active = name
        # Uncheck all others
        for n, (btn, _) in self._buttons.items():
            btn.setChecked(n == name)
        self.process_selected.emit(name)

    @property
    def active_process(self) -> str:
        return self._active
