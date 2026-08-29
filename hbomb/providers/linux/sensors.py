from __future__ import annotations

import os
from hbomb.snapshot.types import EnergySnapshot, ThermalSensor, ThermalSnapshot


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


_last_energy: dict[str, tuple[float, float]] = {}


def sample_energy(governor: str) -> EnergySnapshot:
    watts = _rapl_watts()
    batt = _battery()
    state = governor or "unknown"
    return EnergySnapshot(watts=watts, governor=governor, power_state=state, battery_pct=batt)


def _rapl_watts() -> float | None:
    import time

    base = "/sys/class/powercap"
    if not os.path.isdir(base):
        return None
    now = time.monotonic()
    total = 0.0
    found = False
    try:
        names = os.listdir(base)
    except OSError:
        return None
    for name in names:
        if not name.startswith("intel-rapl") and not name.startswith("amd-"):
            if "rapl" not in name:
                continue
        path = os.path.join(base, name, "energy_uj")
        if ":" in name and name.count(":") > 1:
            continue
        if name.endswith(":0") or name == "intel-rapl:0" or ":0" in name and name.count(":") == 1:
            pass
        elif name.count(":") >= 1 and not name.endswith(":0"):
            if name.count(":") > 1:
                continue
        try:
            uj = float(_read(path).strip())
        except (OSError, ValueError):
            continue
        prev = _last_energy.get(name)
        _last_energy[name] = (now, uj)
        if prev is None:
            continue
        dt = now - prev[0]
        if dt <= 0:
            continue
        du = uj - prev[1]
        if du < 0:
            continue
        total += (du / 1_000_000.0) / dt
        found = True
    if not found:
        return None
    return total if total > 0 else None


def _battery() -> float | None:
    bat = "/sys/class/power_supply"
    try:
        for name in os.listdir(bat):
            if not name.startswith("BAT"):
                continue
            try:
                return float(_read(os.path.join(bat, name, "capacity")).strip())
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return None


def sample_thermals() -> ThermalSnapshot:
    sensors: list[ThermalSensor] = []
    hwmon = "/sys/class/hwmon"
    try:
        chips = os.listdir(hwmon)
    except OSError:
        chips = []
    for chip in chips:
        cdir = os.path.join(hwmon, chip)
        try:
            label = _read(os.path.join(cdir, "name")).strip()
        except OSError:
            label = chip
        try:
            files = os.listdir(cdir)
        except OSError:
            continue
        for fn in files:
            if not (fn.startswith("temp") and fn.endswith("_input")):
                continue
            idx = fn[4:-6]
            name = label
            try:
                nlab = _read(os.path.join(cdir, f"temp{idx}_label")).strip()
                name = f"{label}/{nlab}"
            except OSError:
                name = f"{label}/{fn}"
            try:
                milli = float(_read(os.path.join(cdir, fn)).strip())
            except (OSError, ValueError):
                continue
            temp = milli / 1000.0 if milli > 200 else milli
            kind = "die" if any(k in name.lower() for k in ("tctl", "tdie", "die", "cpu", "edge")) else "pickup"
            sensors.append(ThermalSensor(name=name, temp_c=temp, kind=kind))
    hotspot = max((s.temp_c for s in sensors), default=0.0)
    return ThermalSnapshot(hotspot_c=hotspot, sensors=sensors)
