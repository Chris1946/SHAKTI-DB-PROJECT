"""
PulseTrace Desktop — Diagnostic Dialog
========================================

A premium modal dialog that displays the AI root cause analysis
results in a structured, readable format.

Layout:
  ┌─────────────────────────────────────────────────────────────┐
  │  🔴 Primary Bottleneck: CPU Bound          Severity: ██░ 0.78 │
  │  ─────────────────────────────────────────────────────────── │
  │  CPU is at 94% (3.2σ above baseline). Top consumer:        │
  │  'clang' using 82% CPU.                                     │
  │                                                              │
  │  ┌─ Top Processes ─────────────────────────────────────────┐ │
  │  │ PID   Name       CPU%   MEM%   RSS     Threads          │ │
  │  │ 1234  clang      82.1   4.2    340 MB  12               │ │
  │  │ 5678  node       8.3    12.1   980 MB  24               │ │
  │  └──────────────────────────────────────────────────────────┘ │
  │                                                              │
  │  Recommendation:                                             │
  │  The system is CPU-bound. Process 'clang' is the primary ... │
  │                                                              │
  │                                         [ Close ]            │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


from desktop.ui.theme import Theme

class DiagnosticDialog(QDialog):
    """
    Modal dialog showing the AI root cause analysis.
    """

    def __init__(self, report: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("AI Root Cause Analysis")
        self.setMinimumSize(640, 520)
        self.resize(700, 580)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.get_color('bg_base')};
            }}
        """)
        self._report = report
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Header ──
        header = QLabel("AI Root Cause Analysis")
        hfont = QFont()
        hfont.setPointSize(18)
        hfont.setWeight(QFont.Weight.Bold)
        header.setFont(hfont)
        header.setStyleSheet(f"color: {Theme.get_color('text_primary')};")
        layout.addWidget(header)

        # ── Scrollable content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        content = QWidget()
        clayout = QVBoxLayout(content)
        clayout.setContentsMargins(0, 0, 0, 0)
        clayout.setSpacing(14)

        primary = self._report.get("primary_bottleneck")

        if primary:
            # ── Primary bottleneck card ──
            card = self._make_bottleneck_card(primary, is_primary=True)
            clayout.addWidget(card)
        else:
            no_issue = QLabel("No significant bottleneck detected.")
            no_issue.setStyleSheet(f"color: {Theme.get_color('accent_ok')}; font-size: 15px; font-weight: 600;")
            clayout.addWidget(no_issue)

        # ── Other findings ──
        findings = self._report.get("all_findings", [])
        secondary = [f for f in findings if f != primary and f.get("severity", 0) > 0]
        if secondary:
            sec_header = QLabel("Other Contributing Factors")
            shfont = QFont()
            shfont.setPointSize(13)
            shfont.setWeight(QFont.Weight.Bold)
            sec_header.setFont(shfont)
            sec_header.setStyleSheet(f"color: {Theme.get_color('text_secondary')};")
            clayout.addWidget(sec_header)

            for f in secondary:
                card = self._make_bottleneck_card(f, is_primary=False)
                clayout.addWidget(card)

        # ── Top processes table ──
        processes = self._report.get("top_processes", [])
        if processes:
            proc_header = QLabel("Top Processes at Time of Anomaly")
            phfont = QFont()
            phfont.setPointSize(13)
            phfont.setWeight(QFont.Weight.Bold)
            proc_header.setFont(phfont)
            proc_header.setStyleSheet(f"color: {Theme.get_color('text_secondary')};")
            clayout.addWidget(proc_header)

            table = self._make_process_table(processes)
            clayout.addWidget(table)

        # ── Recommendation ──
        recommendation = self._report.get("recommendation", "")
        if recommendation:
            rec_header = QLabel("Recommendation")
            rfont = QFont()
            rfont.setPointSize(13)
            rfont.setWeight(QFont.Weight.Bold)
            rec_header.setFont(rfont)
            rec_header.setStyleSheet(f"color: {Theme.get_color('text_secondary')};")
            clayout.addWidget(rec_header)

            rec_body = QLabel(recommendation)
            rec_body.setWordWrap(True)
            rec_body.setStyleSheet(f"""
                color: {Theme.get_color('text_primary')};
                font-size: 13px;
                line-height: 1.5;
                background-color: {Theme.get_color('bg_surface')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: 8px;
                padding: 14px;
            """)
            clayout.addWidget(rec_body)

        clayout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # ── Close button ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.get_color('accent')};
                color: #ffffff;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _make_bottleneck_card(self, finding: Dict, is_primary: bool) -> QFrame:
        """Create a card for a bottleneck finding."""
        card = QFrame()
        accent = Theme.get_color('accent') if is_primary else Theme.get_color('border')
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.get_color('bg_surface')};
                border: 1px solid {accent};
                border-radius: 10px;
                {'border-left: 4px solid ' + accent + ';' if is_primary else ''}
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Title row: icon + category + severity bar
        top_row = QHBoxLayout()

        icon_cat = QLabel(f"{finding.get('icon', '●')}  {finding.get('category', 'Unknown')}")
        icf = QFont()
        icf.setPointSize(14 if is_primary else 13)
        icf.setWeight(QFont.Weight.Bold)
        icon_cat.setFont(icf)
        icon_cat.setStyleSheet(f"color: {Theme.get_color('text_primary')};")
        top_row.addWidget(icon_cat)
        top_row.addStretch()

        severity = finding.get("severity", 0)
        sev_label = QLabel(f"Severity: {severity:.0%}")
        sev_label.setStyleSheet(f"color: {Theme.get_color('text_muted')}; font-size: 12px; font-weight: 600;")
        top_row.addWidget(sev_label)

        layout.addLayout(top_row)

        # Severity bar
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(severity * 100))
        bar.setTextVisible(False)
        bar.setFixedHeight(4)
        if severity > 0.7:
            bar_color = Theme.get_color("accent_err")
        elif severity > 0.4:
            bar_color = Theme.get_color("accent_warn")
        else:
            bar_color = Theme.get_color("accent_ok")
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Theme.get_color('bg_alt')};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(bar)

        # Summary
        summary = finding.get("summary", "")
        if summary:
            sum_lbl = QLabel(summary)
            sum_lbl.setWordWrap(True)
            sum_lbl.setStyleSheet(f"color: {Theme.get_color('text_secondary')}; font-size: 13px;")
            layout.addWidget(sum_lbl)

        return card

    def _make_process_table(self, processes: List[Dict]) -> QTableWidget:
        """Create a styled process table."""
        headers = ["PID", "Name", "CPU %", "Mem %", "RSS (MB)", "Threads"]
        table = QTableWidget(len(processes), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFixedHeight(min(36 + len(processes) * 32, 220))

        # Styling handled globally by ThemeManager in theme.py

        h = table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name stretches
        for i in [0, 2, 3, 4, 5]:
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        for row, proc in enumerate(processes):
            table.setItem(row, 0, QTableWidgetItem(str(proc.get("pid", ""))))
            table.setItem(row, 1, QTableWidgetItem(proc.get("name", "")))
            table.setItem(row, 2, QTableWidgetItem(f"{proc.get('cpu_percent', 0):.1f}"))
            table.setItem(row, 3, QTableWidgetItem(f"{proc.get('memory_percent', 0):.1f}"))
            table.setItem(row, 4, QTableWidgetItem(f"{proc.get('memory_rss_mb', 0):.0f}"))
            table.setItem(row, 5, QTableWidgetItem(str(proc.get("threads", 0))))

        return table
