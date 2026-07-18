"""
PulseTrace Desktop — Background Polling Worker
================================================

``PollWorker`` runs the metric-fetching loop inside a dedicated
``QThread`` so the UI event loop is never blocked by network I/O.

Architecture
------------

  Main thread                     PollWorker thread
  ─────────────────────────       ──────────────────────────────
  MainWindow / DashboardPage      PollWorker
     │                               │
     │  worker.start()               │  run() called by Qt
     │ ──────────────────────────►   │
     │                               │  QTimer fires every N ms
     │                               │  → _fetch() called
     │                               │  → MetricService.get_latest()
     │                               │  → emits metrics_received(data)
     │                               │
     │  slot: on_metrics(data)  ◄──  │  (crosses thread boundary safely)
     │  → update widgets             │

Signals
-------
metrics_received(list)  — fired with the raw JSON list from the API.
error_occurred(str)     — fired when the API call fails.
connection_changed(bool)— fired when reachability status changes.

Usage
-----
    worker = PollWorker(interval_ms=5000)
    worker.metrics_received.connect(self.on_metrics)
    worker.connection_changed.connect(main_window.set_connection_status)
    worker.start()
    ...
    worker.stop()
    worker.wait()   # graceful shutdown before app exit
"""

from __future__ import annotations

import logging
from typing import Any, List

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from desktop.config import config
from desktop.services.api_client import APIClientError
from desktop.services.metric_service import MetricService

logger = logging.getLogger(__name__)


class PollWorker(QObject):
    """
    QObject (NOT QThread subclass) designed to be moved to a QThread.

    We use the recommended Qt pattern:
        worker = PollWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start_polling)
        thread.start()

    This avoids subclassing QThread and keeps the worker testable
    without Qt's threading machinery.
    """

    # ------------------------------------------------------------------ #
    # Qt Signals                                                           #
    # ------------------------------------------------------------------ #
    metrics_received   = Signal(list)   # list of metric dicts
    error_occurred     = Signal(str)    # human-readable error string
    connection_changed = Signal(bool)   # True = online, False = offline

    def __init__(self, interval_ms: int | None = None) -> None:
        super().__init__()
        self._interval_ms = interval_ms or config.POLL_INTERVAL_MS
        self._service = MetricService()
        self._timer: QTimer | None = None
        self._connected: bool | None = None   # None = unknown (startup)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    @Slot()
    def start_polling(self) -> None:
        """
        Called when the owner QThread starts.
        Creates a QTimer that fires _fetch() on the worker's thread.
        """
        logger.info(
            "PollWorker starting — interval %d ms", self._interval_ms
        )
        self._timer = QTimer()
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._fetch)
        self._timer.start()

        # Fetch immediately on startup so the UI is not empty for N seconds
        self._fetch()

    @Slot()
    def stop(self) -> None:
        """Cleanly stop the timer before the thread exits."""
        if self._timer is not None:
            self._timer.stop()
            logger.info("PollWorker stopped")

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @Slot()
    def _fetch(self) -> None:
        """Execute one poll cycle — runs on the worker thread."""
        try:
            data: List[Any] = self._service.get_latest_system_metrics()
            self._set_connection(True)
            self.metrics_received.emit(data)
            logger.debug("Fetched %d metric records", len(data))

        except APIClientError as exc:
            self._set_connection(False)
            self.error_occurred.emit(str(exc))
            logger.warning("Poll failed: %s", exc)

    def _set_connection(self, connected: bool) -> None:
        """Emit connection_changed only when state actually changes."""
        if connected != self._connected:
            self._connected = connected
            self.connection_changed.emit(connected)
