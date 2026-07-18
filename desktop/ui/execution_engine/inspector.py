"""
Execution Engine — Inspector Panel (Multi-Mode)

Three display modes:
  DEFAULT   — Node load bar + packet metadata table
  LEARNING  — Rich educational content about the OS subsystem
  DEVELOPER — Syscall signatures, debug commands, bottleneck patterns
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame
from PySide6.QtCore import Qt

from desktop.ui.theme import Theme

# Keys to display with friendly labels, in order
_DISPLAY_KEYS = [
    ("type",        "Type"),
    ("protocol",    "Protocol"),
    ("direction",   "Direction"),
    ("src_ip",      "Source IP"),
    ("src_port",    "Source Port"),
    ("src_host",    "Source Host"),
    ("dst_ip",      "Dest IP"),
    ("dst_port",    "Dest Port"),
    ("dst_host",    "Dest Host"),
    ("process",     "Process"),
    ("operation",   "Operation"),
    ("syscall",     "Syscall"),
    ("engine",      "DB Engine"),
    ("device",      "Device"),
    ("filesystem",  "Filesystem"),
    ("size",        "Size"),
    ("pages",       "Pages"),
    ("rows_est",    "Est. Rows"),
    ("latency_est", "Est. Latency"),
    ("confidence",  "Confidence"),
]

# Keys to hide from display (internal)
_HIDDEN = {"color", "speed", "path"}

# Display modes
MODE_DEFAULT = "default"
MODE_LEARNING = "learning"
MODE_DEVELOPER = "developer"


class InspectorPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setObjectName("InspectorPanel")
        self._mode = MODE_DEFAULT
        self._current_node = None
        self._current_packet = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Mode label at top
        self.mode_label = QLabel("")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)

        self.title = QLabel("Inspector")
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Click a node or packet to inspect...")

        layout.addWidget(self.title)
        layout.addWidget(self.details)

        self._apply_theme()
        Theme.theme_changed.connect(self._apply_theme)

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QFrame#InspectorPanel {{
                background-color: {Theme.get_color('bg_surface')};
                border-radius: 8px;
                border: 1px solid {Theme.get_color('border')};
            }}
        """)
        self.title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Theme.get_color('accent')}; padding-bottom: 4px;")
        self.details.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.get_color('bg_base')};
                color: {Theme.get_color('text_primary')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 6px;
                padding: 8px;
                font-family: monospace;
                font-size: 12px;
            }}
        """)
        self._update_mode_label()

    def set_mode(self, mode: str):
        """Switch display mode and re-render current item."""
        self._mode = mode
        self._update_mode_label()
        # Re-render whatever is currently displayed
        if self._current_node:
            self.inspect_node(self._current_node)
        elif self._current_packet:
            self.inspect_packet(self._current_packet)

    def _update_mode_label(self):
        if self._mode == MODE_LEARNING:
            self.mode_label.setText("🧠 LEARNING MODE")
            self.mode_label.setStyleSheet(
                f"color: #34d399; font-weight: bold; font-size: 10px; "
                f"background: #064e3b; border: 1px solid #34d399; border-radius: 3px; padding: 2px 6px;"
            )
            self.mode_label.show()
        elif self._mode == MODE_DEVELOPER:
            self.mode_label.setText("🛠 DEVELOPER MODE")
            self.mode_label.setStyleSheet(
                f"color: #a78bfa; font-weight: bold; font-size: 10px; "
                f"background: #2e1065; border: 1px solid #a78bfa; border-radius: 3px; padding: 2px 6px;"
            )
            self.mode_label.show()
        else:
            self.mode_label.hide()

    # ── Packet Inspection ──

    def inspect_packet(self, packet):
        self._current_packet = packet
        self._current_node = None

        ptype = packet.metadata.get('type', 'Unknown')
        self.title.setText(ptype)

        html = "<table style='border-collapse:collapse; width:100%;'>"

        # Display ordered keys first
        shown = set()
        for key, label in _DISPLAY_KEYS:
            if key in packet.metadata:
                val = packet.metadata[key]
                html += self._row(label, str(val))
                shown.add(key)

        # Then any extra keys not in the ordered list (skip hidden)
        for key, val in packet.metadata.items():
            if key not in shown and key not in _HIDDEN:
                html += self._row(key.replace("_", " ").title(), str(val))

        html += "</table>"

        # Journey path
        path_names = [n.label for n in packet.path_nodes]
        html += f"<br/><span style='color:{Theme.get_color('text_muted')}; font-size:11px;'>JOURNEY</span><br/>"
        html += f"<span style='color:{Theme.get_color('accent')};'>" + " → ".join(path_names) + "</span>"

        # Traversal timestamps if available
        if hasattr(packet, 'traversal_log') and packet.traversal_log:
            html += f"<br/><br/><span style='color:{Theme.get_color('text_muted')}; font-size:11px;'>TRAVERSAL TIMELINE</span>"
            html += "<table style='border-collapse:collapse; width:100%;'>"
            for entry in packet.traversal_log:
                html += self._row(entry["node"], f"{entry['time']:.3f}s")
            html += "</table>"

        self.details.setHtml(html)

    # ── Node Inspection ──

    def inspect_node(self, node):
        self._current_node = node
        self._current_packet = None

        self.title.setText(node.label)

        if self._mode == MODE_LEARNING:
            self._render_learning(node)
        elif self._mode == MODE_DEVELOPER:
            self._render_developer(node)
        else:
            self._render_default(node)

    def _render_default(self, node):
        """Default mode: basic stats + load bar."""
        load_pct = node.load * 100
        bar_color = "#34d399" if load_pct < 60 else ("#fbbf24" if load_pct < 85 else "#ef4444")

        html = "<table style='border-collapse:collapse; width:100%;'>"
        html += self._row("ID", node.node_id)
        html += self._row("Label", node.label)
        html += self._row("Tier", node.tier.upper() if node.tier else "—")
        html += self._row("Load", f"{load_pct:.1f}%")
        html += "</table>"

        # Visual load bar
        bg = Theme.get_color("bg_base")
        border = Theme.get_color("border")
        html += f"""
        <br/>
        <div style='background:{bg}; border-radius:4px; height:12px; width:100%; border:1px solid {border};'>
            <div style='background:{bar_color}; border-radius:4px; height:12px; width:{min(load_pct, 100):.0f}%;'></div>
        </div>
        """

        # Hint about modes
        accent = Theme.get_color("accent")
        muted = Theme.get_color("text_muted")
        html += f"<br/><p style='color:{muted}; font-size:10px; font-style:italic;'>"
        html += "💡 Enable <b style='color:#34d399;'>Learning Mode</b> to learn about this subsystem, "
        html += "or <b style='color:#a78bfa;'>Developer Mode</b> for debugging commands."
        html += "</p>"

        self.details.setHtml(html)

    def _render_learning(self, node):
        """Learning mode: rich educational content."""
        from desktop.ui.execution_engine.knowledge_base import get_learning_html
        accent = Theme.get_color("accent")
        text = Theme.get_color("text_primary")
        muted = Theme.get_color("text_muted")
        html = get_learning_html(node.node_id, accent, text, muted)
        self.details.setHtml(html)

    def _render_developer(self, node):
        """Developer mode: syscalls, perf counters, debug commands."""
        from desktop.ui.execution_engine.dev_insights import get_developer_html
        accent = Theme.get_color("accent")
        text = Theme.get_color("text_primary")
        muted = Theme.get_color("text_muted")
        html = get_developer_html(node.node_id, accent, text, muted)
        self.details.setHtml(html)

    @staticmethod
    def _row(label: str, value: str) -> str:
        return (
            f"<tr>"
            f"<td style='color:{Theme.get_color('text_muted')}; padding:2px 8px 2px 0; white-space:nowrap; font-size:11px;'>{label}</td>"
            f"<td style='color:{Theme.get_color('text_primary')}; padding:2px 0; font-size:11px;'>{value}</td>"
            f"</tr>"
        )
