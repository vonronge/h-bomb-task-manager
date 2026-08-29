from __future__ import annotations

from hbomb.snapshot.types import MemorySnapshot


def _parse_meminfo(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        bits = rest.split()
        if not bits:
            continue
        try:
            kb = int(bits[0])
        except ValueError:
            continue
        out[key] = kb * 1024
    return out


def _parse_psi(text: str) -> tuple[float, float, float, float]:
    # some avg10=0.00 avg60=0.00 avg300=0.00 total=0
    avg10 = avg60 = avg300 = some = 0.0
    for line in text.splitlines():
        if not line.startswith("some") and not line.startswith("full"):
            continue
        fields = dict(part.split("=", 1) for part in line.split()[1:] if "=" in part)
        try:
            if line.startswith("some"):
                avg10 = float(fields.get("avg10", 0))
                avg60 = float(fields.get("avg60", 0))
                avg300 = float(fields.get("avg300", 0))
                some = float(fields.get("total", 0))
        except ValueError:
            continue
        if line.startswith("some"):
            break
    return avg10, avg60, avg300, some


def sample_memory(meminfo_text: str | None = None, psi_text: str | None = None) -> MemorySnapshot:
    if meminfo_text is None:
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            meminfo_text = fh.read()
    info = _parse_meminfo(meminfo_text)
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    cached = info.get("Cached", 0) + info.get("SReclaimable", 0)
    wired = info.get("Unevictable", 0) + info.get("Mlocked", 0)
    compressed = info.get("Zswap", 0) + info.get("Zswapped", 0)
    # Anonymous pages ≈ application
    application = info.get("AnonPages", info.get("Active(anon)", 0) + info.get("Inactive(anon)", 0))
    committed = info.get("Committed_AS", 0)
    occupied = max(0, total - available)
    expensive = application + wired
    swap_total = info.get("SwapTotal", 0)
    swap_used = max(0, swap_total - info.get("SwapFree", 0))
    avg10 = avg60 = avg300 = some = 0.0
    if psi_text is None:
        try:
            with open("/proc/pressure/memory", "r", encoding="utf-8") as fh:
                psi_text = fh.read()
        except OSError:
            psi_text = ""
    if psi_text:
        avg10, avg60, avg300, some = _parse_psi(psi_text)
    dimm = ""
    try:
        with open("/sys/devices/virtual/dmi/id/product_name", "r", encoding="utf-8") as fh:
            dimm = fh.read().strip()
    except OSError:
        pass
    return MemorySnapshot(
        total_bytes=total,
        available_bytes=available,
        application_bytes=application,
        wired_bytes=wired,
        compressed_bytes=compressed,
        cached_bytes=cached,
        committed_bytes=committed,
        swap_used_bytes=swap_used,
        swap_total_bytes=swap_total,
        occupied_bytes=occupied,
        expensive_bytes=expensive,
        psi_avg10=avg10,
        psi_avg60=avg60,
        psi_avg300=avg300,
        psi_some=some,
        dimm_summary=dimm,
    )
