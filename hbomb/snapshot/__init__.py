from __future__ import annotations

from hbomb.snapshot.types import Snapshot, ProviderHealth
from hbomb.snapshot.history import HistoryBank


def record_fast(history: HistoryBank, snap: Snapshot) -> None:
    t = snap.timestamp
    history.push("cpu_util_pct", t, snap.cpu.overall.total * 100.0)
    history.push("cpu_kernel_pct", t, snap.cpu.overall.kernel * 100.0)
    history.push("cpu_user_pct", t, snap.cpu.overall.user * 100.0)
    history.push("clock_ghz", t, snap.cpu.freq_ghz)
    history.push("temp_c", t, snap.thermals.hotspot_c)
    history.push("mem_used_bytes", t, float(snap.memory.occupied_bytes))
    history.push("mem_used_pct", t, snap.memory.used_ratio * 100.0)
    history.push("gpu_util_pct", t, snap.gpu.util * 100.0)
    if snap.gpu.vram_total > 0:
        history.push("gpu_vram_pct", t, snap.gpu.vram_used / snap.gpu.vram_total * 100.0)
    else:
        history.push("gpu_vram_pct", t, 0.0)
    watts = snap.energy.watts if snap.energy.watts is not None else 0.0
    history.push("power_w", t, watts)
    history.push("disk_r_bps", t, snap.disk.read_bps)
    history.push("disk_w_bps", t, snap.disk.write_bps)
    history.push("disk_busy_pct", t, snap.disk.busy * 100.0)
    history.push("net_r_bps", t, snap.net.rx_bps)
    history.push("net_w_bps", t, snap.net.tx_bps)
    for core in snap.cpu.cores:
        history.push(f"cpu{core.index}_pct", t, core.util.total * 100.0)
        history.push(f"cpu{core.index}_kernel_pct", t, core.util.kernel * 100.0)
    for sensor in snap.thermals.sensors:
        history.push(f"therm_{sensor.name}", t, sensor.temp_c)


def health_label(snap: Snapshot) -> str:
    h = snap.health()
    if h == ProviderHealth.HEALTHY:
        word = "Native providers healthy"
    elif h == ProviderHealth.DEGRADED:
        word = "Native providers degraded"
    else:
        word = "Native providers unavailable"
    return f"{word} • {len(snap.processes)} processes • Generation {snap.generation}"
