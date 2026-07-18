"""
PulseTrace Desktop — OS Explainer
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class OSExplainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        title = QLabel("AI Explanation (LLM)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText("Select an anomaly or incident in the Time Machine to view the AI explanation...")
        self.text_edit.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 8px;")
        layout.addWidget(self.text_edit)
        
    def set_explanation(self, text: str):
        self.text_edit.setText(text)
