from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from hbomb.snapshot.types import CpuSnapshot, CpuUtilization, LogicalCore


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


@dataclass
class _CpuTimes:
    user: int = 0
    nice: int = 0
    system: int = 0
    idle: int = 0
    iowait: int = 0
    irq: int = 0
    softirq: int = 0
    steal: int = 0

    @property
    def total(self) -> int:
        return (
            self.user
            + self.nice
            + self.system
            + self.idle
            + self.iowait
            + self.irq
            + self.softirq
            + self.steal
        )

    @property
    def idle_all(self) -> int:
        return self.idle + self.iowait


def parse_stat_cpu_lines(text: str) -> tuple[_CpuTimes, list[_CpuTimes]]:
    overall = _CpuTimes()
    cores: list[_CpuTimes] = []
    for line in text.splitlines():
        if not line.startswith("cpu"):
            continue
        parts = line.split()
        nums = [int(x) for x in parts[1:9]]
        while len(nums) < 8:
            nums.append(0)
        times = _CpuTimes(*nums[:8])
        if parts[0] == "cpu":
            overall = times
        else:
            cores.append(times)
    return overall, cores


def _delta_util(prev: _CpuTimes, cur: _CpuTimes) -> CpuUtilization:
    dt = cur.total - prev.total
    if dt <= 0:
        return CpuUtilization(0.0, 0.0, 0.0)
    user = (cur.user - prev.user + cur.nice - prev.nice) / dt
    kernel = (cur.system - prev.system + cur.irq - prev.irq + cur.softirq - prev.softirq) / dt
    irq = (cur.irq - prev.irq + cur.softirq - prev.softirq) / dt
    steal = (cur.steal - prev.steal) / dt
    nice = (cur.nice - prev.nice) / dt
    total = max(0.0, 1.0 - (cur.idle_all - prev.idle_all) / dt)
    return CpuUtilization(total=total, user=user, kernel=kernel, nice=nice, irq=irq, steal=steal)


def _freq_ghz(index: int | None = None) -> float:
    candidates = []
    if index is not None:
        candidates.append(
            f"/sys/devices/system/cpu/cpu{index}/cpufreq/scaling_cur_freq"
        )
    candidates.append("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    for path in candidates:
        try:
            khz = int(_read(path).strip())
            return khz / 1_000_000.0
        except (OSError, ValueError):
            continue
    return 0.0


def _base_ghz() -> float:
    for path in (
        "/sys/devices/system/cpu/cpu0/cpufreq/base_frequency",
        "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq",
    ):
        try:
            khz = int(_read(path).strip())
            if "base" in path:
                return khz / 1_000_000.0
        except (OSError, ValueError):
            continue
    try:
        for line in _read("/proc/cpuinfo").splitlines():
            if line.lower().startswith("cpu mhz"):
                return float(line.split(":")[1].strip()) / 1000.0
    except (OSError, ValueError):
        pass
    return 0.0


def _governor() -> str:
    try:
        return _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").strip()
    except OSError:
        return ""


def _driver() -> str:
    try:
        return _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver").strip()
    except OSError:
        return ""


def _topology() -> tuple[int, int, int, dict[int, int], set[int]]:
    present = []
    try:
        names = os.listdir("/sys/devices/system/cpu")
    except OSError:
        names = []
    for name in names:
        if name.startswith("cpu") and name[3:].isdigit():
            present.append(int(name[3:]))
    present.sort()
    logical = len(present) or os.cpu_count() or 1
    cores_seen: set[tuple[int, int]] = set()
    sockets: set[int] = set()
    numa: dict[int, int] = {}
    e_cores: set[int] = set()
    for i in present:
        base = f"/sys/devices/system/cpu/cpu{i}"
        try:
            pkg = int(_read(f"{base}/topology/physical_package_id").strip())
        except (OSError, ValueError):
            pkg = 0
        try:
            cid = int(_read(f"{base}/topology/core_id").strip())
        except (OSError, ValueError):
            cid = i
        sockets.add(pkg)
        cores_seen.add((pkg, cid))
        node = 0
        try:
            for entry in os.listdir(f"{base}/node"):
                if entry.startswith("node") and entry[4:].isdigit():
                    node = int(entry[4:])
        except OSError:
            for n in range(8):
                if os.path.exists(f"/sys/devices/system/node/node{n}/cpu{i}"):
                    node = n
                    break
        numa[i] = node
    caps: dict[int, int] = {}
    for i in present:
        try:
            caps[i] = int(_read(f"/sys/devices/system/cpu/cpu{i}/cpu_capacity").strip())
        except (OSError, ValueError):
            continue
    if caps:
        mx = max(caps.values())
        if min(caps.values()) < mx:
            e_cores = {i for i, c in caps.items() if c < mx}
    return len(sockets) or 1, len(cores_seen) or logical, logical, numa, e_cores


def _model_name() -> str:
    try:
        for line in _read("/proc/cpuinfo").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def _cache_summary() -> str:
    parts = []
    for index, label in ((1, "L1"), (2, "L2"), (3, "L3")):
        path = f"/sys/devices/system/cpu/cpu0/cache/index{index}/size"
        try:
            parts.append(f"{label} {_read(path).strip()}")
        except OSError:
            continue
    return ", ".join(parts)


def _virt() -> str:
    try:
        flags = ""
        for line in _read("/proc/cpuinfo").splitlines():
            if line.startswith("flags"):
                flags = line
                break
        if "svm" in flags or "vmx" in flags:
            return "Supported"
    except OSError:
        pass
    return "Unknown"


def _uptime() -> float:
    try:
        return float(_read("/proc/uptime").split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


class CpuSampler:
    def __init__(self) -> None:
        self._prev_all = _CpuTimes()
        self._prev_cores: list[_CpuTimes] = []
        self._topo = _topology()

    def sample(self, process_count: int = 0, thread_count: int = 0) -> CpuSnapshot:
        try:
            text = _read("/proc/stat")
        except OSError:
            text = "cpu 0 0 0 0 0 0 0 0\n"
        overall_t, core_t = parse_stat_cpu_lines(text)
        overall = _delta_util(self._prev_all, overall_t)
        cores: list[LogicalCore] = []
        sockets, physical, logical, numa, e_cores = self._topo
        for i, times in enumerate(core_t):
            prev = self._prev_cores[i] if i < len(self._prev_cores) else _CpuTimes()
            util = _delta_util(prev, times)
            cores.append(
                LogicalCore(
                    index=i,
                    util=util,
                    freq_ghz=_freq_ghz(i),
                    is_efficiency=i in e_cores,
                    numa_node=numa.get(i, 0),
                )
            )
        self._prev_all = overall_t
        self._prev_cores = core_t
        avg_freq = sum(c.freq_ghz for c in cores) / len(cores) if cores else _freq_ghz()
        return CpuSnapshot(
            overall=overall,
            cores=cores,
            freq_ghz=avg_freq,
            base_ghz=_base_ghz(),
            sockets=sockets,
            physical_cores=physical,
            logical_processors=logical or len(cores),
            caches=_cache_summary(),
            virtualization=_virt(),
            governor=_governor(),
            freq_driver=_driver(),
            uptime_s=_uptime(),
            process_count=process_count,
            thread_count=thread_count,
            model_name=_model_name(),
        )
