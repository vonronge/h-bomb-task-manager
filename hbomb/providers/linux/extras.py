from __future__ import annotations

import configparser
import os
import pwd
from dataclasses import dataclass, field


@dataclass
class UnitRow:
    name: str
    description: str
    active: str
    enabled: str
    user_unit: bool


def list_user_units() -> list[UnitRow]:
    rows: list[UnitRow] = []
    home = os.path.expanduser("~/.config/systemd/user")
    if os.path.isdir(home):
        for name in sorted(os.listdir(home)):
            if name.endswith(".service") or name.endswith(".timer"):
                rows.append(UnitRow(name, "", "unknown", "enabled", True))
    return rows


def list_system_units_readonly() -> list[UnitRow]:
    rows: list[UnitRow] = []
    try:
        import dbus  # type: ignore
    except ImportError:
        dbus = None
    if dbus is not None:
        try:
            bus = dbus.SystemBus()
            systemd = bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
            iface = dbus.Interface(systemd, "org.freedesktop.systemd1.Manager")
            for u in iface.ListUnits():
                name, desc, load, active, sub, _follow, _path, _job_id, _job_type, _job_path = u[:10]
                rows.append(UnitRow(str(name), str(desc), f"{active}/{sub}", str(load), False))
            return rows
        except Exception:
            pass
    for path in ("/lib/systemd/system", "/usr/lib/systemd/system"):
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            if name.endswith(".service"):
                rows.append(UnitRow(name, "", "unknown", "static", False))
        break
    return rows[:400]
