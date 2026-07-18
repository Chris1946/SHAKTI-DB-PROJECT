"""
PulseTrace Desktop — Application Entry Point
============================================

Run with:
    cd /path/to/PulseTrace
    python -m desktop.main

or after installing the package:
    pulsetrace-desktop
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from desktop.ui.main_window import MainWindow
from desktop.ui.theme import Theme

# ---------------------------------------------------------------------------
# Logging configuration — INFO by default, DEBUG if -v flag is passed
# ---------------------------------------------------------------------------

LOG_LEVEL = logging.DEBUG if "--verbose" in sys.argv or "-v" in sys.argv else logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pulsetrace.desktop")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Entry point for the PulseTrace desktop application.

    Returns the process exit code (0 = success).
    """
    logger.info("Starting PulseTrace Desktop")

    # High-DPI support (Qt6 enables this automatically, but being explicit
    # makes the intent clear and handles edge cases on some Linux compositors)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PulseTrace")
    app.setApplicationVersion("0.2.0")
    app.setOrganizationName("PulseTrace Open Source")

    # Apply the global stylesheet
    app.setStyleSheet(Theme.get_qss())

    # Use the pristine native system font
    default_font = QFont(".AppleSystemUIFont", 13)
    app.setFont(default_font)

    from desktop.bootstrapper import BootstrapperThread

    # Create and show the main window
    window = MainWindow()

    # Start the bootstrapper
    bootstrapper = BootstrapperThread()
    window._bootstrapper = bootstrapper # keep a reference so it isn't garbage collected
    bootstrapper.status_update.connect(lambda msg: window.statusBar().showMessage(msg))
    bootstrapper.start()

    window.show()

    logger.info("PulseTrace Desktop window opened")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
