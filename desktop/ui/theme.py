"""
PulseTrace Desktop — UI Theme Manager
=====================================

A dynamic theme manager providing native macOS Light and Dark palettes.
"""

from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal

# ──────────────────────────────────────────────────────────────
# Palettes
# ──────────────────────────────────────────────────────────────

LIGHT_PALETTE = {
    "bg_base": "#ececec",        # Mac OS Window Background
    "bg_surface": "#ffffff",     # Mac OS Content Background
    "bg_alt": "#f5f5f5",         # Alternate row background
    "bg_sidebar": "#f5f5f7",     # Simulated vibrant sidebar
    
    "text_primary": "#000000",
    "text_secondary": "#666666",
    "text_muted": "#999999",
    
    "accent": "#007aff",         # Mac OS Native Blue
    "accent_sec": "#5856d6",     # Purple
    "accent_err": "#ff3b30",     # Red
    "accent_warn": "#ffcc00",    # Yellow
    "accent_ok": "#34c759",      # Green
    
    "border": "#e5e5ea",
    "divider": "#d1d1d6",
}

DARK_PALETTE = {
    "bg_base": "#1e1e1e",        # Mac OS Window Background Dark
    "bg_surface": "#2c2c2e",     # Mac OS Content Background Dark
    "bg_alt": "#3a3a3c",         # Alternate row background
    "bg_sidebar": "#282828",     # Simulated vibrant sidebar
    
    "text_primary": "#ffffff",
    "text_secondary": "#ebebf5", # Secondary label
    "text_muted": "#8e8e93",     # Tertiary label
    
    "accent": "#0a84ff",         # Mac OS Native Blue Dark
    "accent_sec": "#5e5ce6",     # Purple Dark
    "accent_err": "#ff453a",     # Red Dark
    "accent_warn": "#ffd60a",    # Yellow Dark
    "accent_ok": "#30d158",      # Green Dark
    
    "border": "#38383a",
    "divider": "#48484a",
}

class _ThemeManager(QObject):
    theme_changed = Signal()

    def __init__(self):
        super().__init__()
        self._is_dark = False

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def toggle(self):
        self.set_dark_mode(not self._is_dark)

    def set_dark_mode(self, dark: bool):
        if self._is_dark != dark:
            self._is_dark = dark
            self.theme_changed.emit()

    def get_color(self, key: str) -> str:
        palette = DARK_PALETTE if self._is_dark else LIGHT_PALETTE
        return palette.get(key, "#ff00ff")  # Magenta fallback

    def get_qss(self) -> str:
        p = DARK_PALETTE if self._is_dark else LIGHT_PALETTE
        return f"""
/* ─── Base ─── */
QWidget {{
    background-color: {p["bg_base"]};
    color: {p["text_primary"]};
    font-size: 13px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}}

QLabel {{
    background-color: transparent;
}}

QFrame {{
    border: none;
}}

/* ─── Sidebar ─── */
QFrame#sidebar {{
    background-color: {p["bg_sidebar"]};
    border-right: 1px solid {p["border"]};
    min-width: 220px;
    max-width: 220px;
}}
QFrame#sidebar QWidget {{
    background-color: transparent;
}}

/* Brand text */
QLabel#brand_pulse {{
    color: {p["text_primary"]};
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 2px;
}}
QLabel#brand_dot {{
    color: {p["accent"]};
    font-size: 12px;
}}
QLabel#brand_sub {{
    color: {p["text_muted"]};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
}}

/* Nav list */
QWidget#sidebar_divider {{
    background-color: {p["border"]};
}}
QListWidget#nav_list {{
    background: transparent;
    border: none;
    outline: none;
    padding: 12px 16px;
}}
QListWidget#nav_list::item {{
    color: {p["text_secondary"]};
    padding: 8px 12px;
    border-radius: 8px;
    margin: 2px 0px;
    font-weight: 500;
    font-size: 13px;
}}
QListWidget#nav_list::item:hover {{
    background-color: {p["border"]};
    color: {p["text_primary"]};
}}
QListWidget#nav_list::item:selected {{
    background-color: {p["accent"]};
    color: #ffffff;
    font-weight: 600;
}}

/* ─── Page Header ─── */
QLabel#page_title {{
    color: {p["text_primary"]};
    font-size: 26px;
    font-weight: 700;
    padding: 24px 24px 2px 24px;
}}
QLabel#page_subtitle {{
    color: {p["text_muted"]};
    font-size: 13px;
    font-weight: 400;
    padding: 0px 24px 12px 24px;
}}

/* ─── Cards / GroupBoxes ─── */
QGroupBox {{
    background-color: {p["bg_surface"]};
    border: 1px solid {p["border"]};
    border-radius: 10px;
    margin-top: 1.5em;
    font-weight: 600;
    font-size: 13px;
    color: {p["text_primary"]};
    padding: 16px 12px 12px 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 18px;
    padding: 0 8px;
    color: {p["text_primary"]};
    background: transparent;
}}

/* ─── Status indicators ─── */
QLabel#status_indicator_ok {{
    color: {p["accent_ok"]};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#status_indicator_warn {{
    color: {p["accent_warn"]};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#status_indicator_crit {{
    color: {p["accent_err"]};
    font-size: 11px;
    font-weight: 600;
}}

/* ─── Sidebar Theme Toggle ─── */
QPushButton#btn_theme {{
    background: transparent;
    border: none;
    color: {p["text_secondary"]};
    text-align: left;
    padding: 8px 18px;
    font-weight: 500;
}}
QPushButton#btn_theme:hover {{
    color: {p["text_primary"]};
}}

/* ─── Status Bar ─── */
QLabel#status_text {{
    color: {p["text_muted"]};
    font-size: 11px;
    padding: 0 6px;
}}

QStatusBar {{
    background-color: {p["bg_surface"]};
    border-top: 1px solid {p["border"]};
    color: {p["text_muted"]};
    font-size: 11px;
    padding: 2px 12px;
}}

/* ─── Scrollbars ─── */
QScrollBar:vertical {{
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {p["divider"]};
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p["text_muted"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    height: 0px;
}}

/* ─── ScrollArea ─── */
QScrollArea {{
    background: transparent;
    border: none;
}}

/* ─── Tables ─── */
QTableView, QTableWidget {{
    background-color: transparent;
    border: none;
    color: {p["text_primary"]};
    gridline-color: {p["border"]};
}}
QHeaderView::section {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {p["border"]};
    padding: 8px 4px;
    font-weight: 700;
    color: {p["text_secondary"]};
}}
QTableView::item, QTableWidget::item {{
    border-bottom: 1px solid {p["divider"]};
    padding: 10px 4px;
}}
QTableView::item:hover, QTableWidget::item:hover {{
    background-color: {p["bg_alt"]};
}}

/* ─── Checkboxes ─── */
QCheckBox {{
    color: {p["text_secondary"]};
    font-size: 13px;
    spacing: 6px;
}}
"""

# Global singleton
Theme = _ThemeManager()
