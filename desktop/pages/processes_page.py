"""
PulseTrace Desktop — Processes Page
=====================================

A professional process-list view modelled after Windows Task Manager
and macOS Activity Monitor.

Layout
------

  ┌──────────────────────────────────────────────────────────────────┐
  │  [ ↺ Refresh ]    [ Search: __________ ]       25 processes      │
  ├──────────────────────────────────────────────────────────────────┤
  │  PID  │  Name         │  User    │  CPU %  │  Mem %  │  RSS      │
  │──────────────────────────────────────────────────────────────────│
  │  1234 │  python3      │  chris   │  42.1   │  3.5    │  142 MB   │
  │   331 │  postgres     │  postgres│   1.2   │  1.1    │   44 MB   │
  │  …                                                                │
  └──────────────────────────────────────────────────────────────────┘

Architecture
------------
- ``ProcessTableModel`` (QAbstractTableModel):
    Holds the data and implements the Qt model protocol.
    Column sorting is handled via QSortFilterProxyModel.
    No subclassing of QTableWidget — this is the production pattern.

- ``ProcessesPage`` (QWidget):
    Owns the model, proxy, view, and a dedicated poll worker.
    Separates UI concerns from data concerns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    QThread,
    Slot,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from desktop.services.poll_worker import PollWorker
from desktop.services.metric_service import MetricService
from desktop.ui.theme import Theme

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _fmt_bytes(b: float) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

_COLUMNS = [
    ("PID",      "pid",            False),   # (header, data key, is_numeric_sort)
    ("Name",     "name",           False),
    ("User",     "username",       False),
    ("Status",   "status",         False),
    ("CPU %",    "cpu_percent",    True),
    ("Mem %",    "memory_percent", True),
    ("RSS",      "memory_rss",     True),
    ("Threads",  "num_threads",    True),
]

_HEADER    = [c[0] for c in _COLUMNS]
_KEYS      = [c[1] for c in _COLUMNS]
_NUMERIC   = {i for i, c in enumerate(_COLUMNS) if c[2]}


# ---------------------------------------------------------------------------
# Table Model
# ---------------------------------------------------------------------------

class ProcessTableModel(QAbstractTableModel):
    """
    Custom ``QAbstractTableModel`` for process metrics.

    This approach is preferred over ``QTableWidget`` because:
    - It separates data from presentation.
    - It works seamlessly with ``QSortFilterProxyModel`` for sorting/filtering.
    - It handles large datasets efficiently via virtual data access.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Qt Model Protocol — REQUIRED overrides                              #
    # ------------------------------------------------------------------ #

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        if row >= len(self._data) or col >= len(_KEYS):
            return None

        record = self._data[row]
        key    = _KEYS[col]
        value  = record.get(key)

        if role == Qt.ItemDataRole.DisplayRole:
            if value is None:
                return "—"
            if key == "memory_rss":
                return _fmt_bytes(float(value))
            if key in ("cpu_percent", "memory_percent"):
                return f"{float(value):.1f}"
            return str(value)

        if role == Qt.ItemDataRole.UserRole:
            # Raw value for proxy model sort (numeric sort needs the raw float)
            return float(value) if (col in _NUMERIC and value is not None) else value

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in _NUMERIC:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        if role == Qt.ItemDataRole.ForegroundRole:
            from PySide6.QtGui import QColor
            if key == "cpu_percent" and value is not None:
                v = float(value)
                if v >= 50:
                    return QColor(Theme.get_color("accent_err"))   # high CPU
                if v >= 20:
                    return QColor(Theme.get_color("accent_warn"))   # moderate
            if key == "status" and value == "zombie":
                return QColor(Theme.get_color("accent_err"))

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return _HEADER[section] if section < len(_HEADER) else None
        return None

    # ------------------------------------------------------------------ #
    # Data mutation                                                        #
    # ------------------------------------------------------------------ #

    def refresh(self, records: List[Dict[str, Any]]) -> None:
        """
        Replace all data with a new snapshot and notify the view.

        Uses ``beginResetModel`` / ``endResetModel`` which is correct
        when the entire dataset is replaced at once (the common polling case).
        """
        self.beginResetModel()
        self._data = records
        self.endResetModel()


# ---------------------------------------------------------------------------
# Processes Poll Worker (wraps PollWorker with process-specific fetch)
# ---------------------------------------------------------------------------

class ProcessPollWorker(PollWorker):
    """
    A specialised PollWorker that fetches process data instead of
    system metrics.

    We override ``_fetch`` to call ``get_latest_processes`` and
    reuse the same ``metrics_received`` signal (list payload).
    """

    def __init__(self, interval_ms: int | None = None) -> None:
        super().__init__(interval_ms)

    @Slot()
    def _fetch(self) -> None:  # type: ignore[override]
        try:
            data = self._service.get_latest_processes(limit=50)
            self._set_connection(True)
            self.metrics_received.emit(data)
            logger.debug("Fetched %d process records", len(data))
        except Exception as exc:
            from desktop.services.api_client import APIClientError
            if isinstance(exc, APIClientError):
                self._set_connection(False)
                self.error_occurred.emit(str(exc))
            logger.warning("Process poll failed: %s", exc)


# ---------------------------------------------------------------------------
# Processes Page
# ---------------------------------------------------------------------------

class ProcessesPage(QWidget):
    """
    Process list page using a ``QTableView`` + ``QAbstractTableModel``.

    Parameters
    ----------
    on_connection_changed:  Callable(bool) forwarded to MainWindow status bar.
    parent:                 Standard Qt parent.
    """

    def __init__(
        self,
        on_connection_changed=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_connection_changed = on_connection_changed
        self._model = ProcessTableModel(self)
        self._build_ui()
        self._start_worker()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(12)

        # ---- Toolbar ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.setFixedWidth(110)
        self._btn_refresh.setToolTip("Manually trigger a data refresh")
        self._btn_refresh.clicked.connect(self._manual_refresh)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by name or user…")
        self._search.setFixedWidth(240)
        self._search.setClearButtonEnabled(True)

        self._count_label = QLabel("0 processes")
        self._count_label.setObjectName("status_text")

        toolbar.addWidget(self._btn_refresh)
        toolbar.addWidget(self._search)
        toolbar.addStretch()
        toolbar.addWidget(self._count_label)
        layout.addLayout(toolbar)

        # ---- Proxy model (sorting + filtering) ----
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        # Filter on Name (col 1) and User (col 2) simultaneously
        self._proxy.setFilterKeyColumn(-1)    # -1 = all columns

        self._search.textChanged.connect(self._proxy.setFilterFixedString)

        # ---- Table view ----
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().hide()
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Column sizing
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # PID
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)            # Name
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # User
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # CPU%
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Mem%
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # RSS
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Threads

        # Default sort: CPU % descending
        self._table.sortByColumn(4, Qt.SortOrder.DescendingOrder)

        layout.addWidget(self._table)

    # ------------------------------------------------------------------ #
    # Background worker                                                    #
    # ------------------------------------------------------------------ #

    def _start_worker(self) -> None:
        self._worker = ProcessPollWorker()
        self._thread = QThread(self)

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_polling)
        self._thread.finished.connect(self._worker.deleteLater)

        self._worker.metrics_received.connect(self._on_processes)
        self._worker.error_occurred.connect(self._on_error)

        if self._on_connection_changed is not None:
            self._worker.connection_changed.connect(self._on_connection_changed)

        self._thread.start()
        logger.info("ProcessesPage: poll worker thread started")

    def stop_worker(self) -> None:
        """Graceful shutdown — call from MainWindow.closeEvent()."""
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self._worker, "stop", Qt.ConnectionType.BlockingQueuedConnection
        )
        self._thread.quit()
        self._thread.wait()
        logger.info("ProcessesPage: poll worker thread stopped")

    def _manual_refresh(self) -> None:
        """Immediately request a new data fetch from the worker."""
        # We invoke _fetch() on the worker's thread to stay thread-safe
        from PySide6.QtCore import QMetaObject, Qt as QtNS
        QMetaObject.invokeMethod(self._worker, "_fetch", QtNS.ConnectionType.QueuedConnection)

    # ------------------------------------------------------------------ #
    # Slots                                                                #
    # ------------------------------------------------------------------ #

    @Slot(list)
    def _on_processes(self, data: List[Dict[str, Any]]) -> None:
        self._model.refresh(data)
        visible = self._proxy.rowCount()
        total   = self._model.rowCount()
        self._count_label.setText(
            f"{visible} of {total} processes" if visible != total
            else f"{total} processes"
        )

    @Slot(str)
    def _on_error(self, message: str) -> None:
        logger.warning("Processes poll error: %s", message)
        self._count_label.setText("Backend unreachable")
