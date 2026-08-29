from __future__ import annotations


def bytes_h(n: float | int) -> str:
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


def compact_bytes(n: float | int) -> str:
    """Short size label for treemap tiles."""
    n = float(n)
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024 or unit == "T":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} T"


def bps_h(n: float) -> str:
    return bytes_h(n) + "/s"


def hz_h(ghz: float) -> str:
    if ghz >= 1:
        return f"{ghz:.2f} GHz"
    return f"{ghz * 1000:.0f} MHz"


def pct_h(x: float) -> str:
    return f"{x * 100:.1f}%"


def uptime_h(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{d}:{h:02d}:{m:02d}:{s:02d}"
