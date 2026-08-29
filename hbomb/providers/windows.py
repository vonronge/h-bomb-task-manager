"""Windows provider slot.

A later port fills the same Snapshot types (CpuUtilization, MemorySnapshot, …)
from PDH/WMI. The Qt UI does not change.
"""

from __future__ import annotations


class WindowsCollector:
    def collect(self, *args, **kwargs):
        raise NotImplementedError("Windows provider is not in v1")
