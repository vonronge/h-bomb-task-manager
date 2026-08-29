from __future__ import annotations

import os
import time
import traceback

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, QMutex, QMutexLocker, Slot

from hbomb.providers.linux import LinuxCollector
from hbomb.providers.linux.processes import child_pids_of
from hbomb.snapshot import record_fast
from hbomb.snapshot.history import HistoryBank
from hbomb.snapshot.types import Snapshot


class _Worker(QObject):
    snapshot_ready = Signal(object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._collector: LinuxCollector | None = None
        self._gen = 0
        self._tick = 0
        self._self_pid = os.getpid()
        self._pids = frozenset({self._self_pid})
        self._timer: QTimer | None = None

    @Slot()
    def start_timer(self) -> None:
        self._collector = LinuxCollector()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self.step)
        self._timer.start()

    @Slot()
    def stop_timer(self) -> None:
        if self._timer:
            self._timer.stop()

    def step(self) -> None:
        if self._collector is None:
            return
        try:
            now = time.time()
            self._gen += 1
            self._tick += 1
            full = self._tick % 10 == 1
            if full:
                self._pids = frozenset(child_pids_of(self._self_pid))
            snap = self._collector.collect(
                self._gen, now, self._pids, sample_procs=full, sample_heavy=full
            )
            self.snapshot_ready.emit(snap)
        except Exception:
            self.failed.emit(traceback.format_exc())


class SnapshotEngine(QObject):
    """Cheap counters at ~60 Hz on a worker thread. Process table ~1 Hz."""

    updated = Signal(object)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.history = HistoryBank()
        self._latest: Snapshot | None = None
        self._mutex = QMutex()
        self._thread = QThread(self)
        self._worker = _Worker()
        self._worker.moveToThread(self._thread)
        self._worker.snapshot_ready.connect(self._on_snap)
        self._worker.failed.connect(self.error.emit)
        self._thread.started.connect(self._worker.start_timer)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        from PySide6.QtCore import QMetaObject, Qt as _Qt

        QMetaObject.invokeMethod(self._worker, "stop_timer", _Qt.ConnectionType.QueuedConnection)
        self._thread.quit()
        self._thread.wait(1500)

    def _on_snap(self, snap: Snapshot) -> None:
        record_fast(self.history, snap)
        with QMutexLocker(self._mutex):
            self._latest = snap
        self.updated.emit(snap)

    def latest(self) -> Snapshot | None:
        with QMutexLocker(self._mutex):
            return self._latest
