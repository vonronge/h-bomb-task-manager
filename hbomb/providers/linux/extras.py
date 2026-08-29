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
    # User-mode only: systemd --user via D-Bus would be better; fall back to listing unit files.
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
    # Fallback: list unit names without controlling them
    for path in ("/lib/systemd/system", "/usr/lib/systemd/system"):
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            if name.endswith(".service"):
                rows.append(UnitRow(name, "", "unknown", "static", False))
        break
    return rows[:400]


@dataclass
class AutostartRow:
    name: str
    path: str
    enabled: bool
    command: str
    user_file: bool


def list_autostart() -> list[AutostartRow]:
    rows: list[AutostartRow] = []
    dirs = [
        (os.path.expanduser("~/.config/autostart"), True),
        ("/etc/xdg/autostart", False),
    ]
    for folder, user_file in dirs:
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".desktop"):
                continue
            path = os.path.join(folder, fn)
            cfg = configparser.ConfigParser(interpolation=None)
            try:
                cfg.read(path)
                entry = cfg["Desktop Entry"]
            except Exception:
                continue
            hidden = entry.get("Hidden", "false").lower() == "true"
            only_show = entry.get("OnlyShowIn", "")
            name = entry.get("Name", fn)
            cmd = entry.get("Exec", "")
            rows.append(AutostartRow(name, path, not hidden, cmd, user_file))
    return rows


def toggle_autostart(path: str, enabled: bool) -> bool:
    if not path.startswith(os.path.expanduser("~/.config/autostart")):
        return False
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str  # type: ignore
    cfg.read(path)
    if "Desktop Entry" not in cfg:
        return False
    cfg["Desktop Entry"]["Hidden"] = "false" if enabled else "true"
    with open(path, "w", encoding="utf-8") as fh:
        cfg.write(fh, space_around_delimiters=False)
    return True


@dataclass
class SessionRow:
    user: str
    uid: int
    session: str
    seat: str
    tty: str
    state: str
    leader: int


def list_sessions() -> list[SessionRow]:
    rows: list[SessionRow] = []
    try:
        import dbus  # type: ignore
    except ImportError:
        dbus = None
    if dbus is not None:
        try:
            bus = dbus.SystemBus()
            login = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
            iface = dbus.Interface(login, "org.freedesktop.login1.Manager")
            for s in iface.ListSessions():
                sid, uid, user, seat, path = s[:5]
                rows.append(
                    SessionRow(str(user), int(uid), str(sid), str(seat), "", "online", 0)
                )
            return rows
        except Exception:
            pass
    # Fallback: who-like from /proc
    seen: set[str] = set()
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            st = os.stat(f"/proc/{name}")
            user = pwd.getpwuid(st.st_uid).pw_name
        except (OSError, KeyError):
            continue
        if user in seen:
            continue
        seen.add(user)
        rows.append(SessionRow(user, st.st_uid, "", "", "", "active", int(name)))
    return rows


@dataclass
class SockRow:
    proto: str
    local: str
    remote: str
    state: str
    pid: int
    process: str


_TCP_STATE = {
    "01": "ESTABLISHED",
    "02": "SYN_SENT",
    "03": "SYN_RECV",
    "04": "FIN_WAIT1",
    "05": "FIN_WAIT2",
    "06": "TIME_WAIT",
    "07": "CLOSE",
    "08": "CLOSE_WAIT",
    "09": "LAST_ACK",
    "0A": "LISTEN",
    "0B": "CLOSING",
}


def _hex_ip(h: str) -> str:
    if len(h) == 8:
        b = bytes.fromhex(h)
        return ".".join(str(x) for x in reversed(b))
    if len(h) == 32:
        parts = [h[i : i + 4] for i in range(0, 32, 4)]
        return ":".join(parts)
    return h


def list_connections(proc_names: dict[int, str] | None = None) -> list[SockRow]:
    proc_names = proc_names or {}
    inode_pid = _inode_map()
    rows: list[SockRow] = []
    for path, proto in (
        ("/proc/net/tcp", "tcp"),
        ("/proc/net/tcp6", "tcp6"),
        ("/proc/net/udp", "udp"),
        ("/proc/net/udp6", "udp6"),
    ):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()[1:]
        except OSError:
            continue
        for line in lines:
            parts = line.split()
            if len(parts) < 10:
                continue
            lip, lp = parts[1].split(":")
            rip, rp = parts[2].split(":")
            st = _TCP_STATE.get(parts[3].upper(), parts[3]) if proto.startswith("tcp") else "UDP"
            inode = parts[9]
            pid = inode_pid.get(inode, 0)
            rows.append(
                SockRow(
                    proto=proto,
                    local=f"{_hex_ip(lip)}:{int(lp, 16)}",
                    remote=f"{_hex_ip(rip)}:{int(rp, 16)}",
                    state=st,
                    pid=pid,
                    process=proc_names.get(pid, ""),
                )
            )
    return rows


def _inode_map() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        pids = [n for n in os.listdir("/proc") if n.isdigit()]
    except OSError:
        return out
    for pid in pids:
        fd_dir = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if target.startswith("socket:["):
                out[target[8:-1]] = int(pid)
    return out


@dataclass
class AppRow:
    name: str
    version: str
    source: str
    size_est: str
    desktop: str


def list_installed_apps() -> list[AppRow]:
    rows: list[AppRow] = []
    seen: set[str] = set()
    dirs = [
        os.path.expanduser("~/.local/share/applications"),
        "/usr/share/applications",
        "/usr/local/share/applications",
    ]
    for folder in dirs:
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".desktop") or fn in seen:
                continue
            seen.add(fn)
            path = os.path.join(folder, fn)
            cfg = configparser.ConfigParser(interpolation=None)
            try:
                cfg.read(path)
                e = cfg["Desktop Entry"]
            except Exception:
                continue
            if e.get("NoDisplay", "false").lower() == "true":
                continue
            if e.get("Type", "Application") != "Application":
                continue
            rows.append(
                AppRow(
                    name=e.get("Name", fn),
                    version=e.get("Version", ""),
                    source=_pkg_source(folder),
                    size_est="",
                    desktop=path,
                )
            )
    return rows


def _pkg_source(folder: str) -> str:
    if "flatpak" in folder:
        return "flatpak"
    if folder.startswith("/usr"):
        return "deb"
    return "user"


def hardware_tree() -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []

    def add(k: str, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                items.append((k, fh.read().strip()))
        except OSError:
            pass

    add("OS", "/etc/os-release")
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            data = dict(
                line.split("=", 1) for line in fh if "=" in line and not line.startswith("#")
            )
            items.append(("Pretty name", data.get("PRETTY_NAME", "").strip('"')))
            items.append(("Version", data.get("VERSION", "").strip('"')))
    except OSError:
        pass
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8") as fh:
            items.append(("Kernel", fh.read().strip()))
    except OSError:
        pass
    add("Hostname", "/etc/hostname")
    add("Board vendor", "/sys/class/dmi/id/board_vendor")
    add("Board name", "/sys/class/dmi/id/board_name")
    add("Product", "/sys/class/dmi/id/product_name")
    add("BIOS", "/sys/class/dmi/id/bios_version")
    items.append(("Desktop", os.environ.get("XDG_CURRENT_DESKTOP", "unknown")))
    return items


def list_mounts() -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    try:
        with open("/proc/self/mountinfo", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return rows
    for line in lines:
        # mountinfo: ... - fstype source superopts
        if " - " not in line:
            continue
        left, right = line.split(" - ", 1)
        left_parts = left.split()
        right_parts = right.split()
        mp = left_parts[4].replace("\\040", " ")
        fstype = right_parts[0]
        src = right_parts[1]
        try:
            st = os.statvfs(mp)
            total = st.f_blocks * st.f_frsize
            used = (st.f_blocks - st.f_bfree) * st.f_frsize
            human = f"{used / (1024**3):.1f} / {total / (1024**3):.1f} GiB"
        except OSError:
            human = ""
        rows.append((mp, src, fstype, human))
    return rows


def journal_tail(n: int = 80) -> list[str]:
    import subprocess

    try:
        out = subprocess.run(
            ["journalctl", "--user", "-n", str(n), "--no-pager", "-o", "short"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.splitlines()
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        out = subprocess.run(
            ["journalctl", "-n", str(n), "--no-pager", "-o", "short"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return out.stdout.splitlines() if out.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        return []


@dataclass
class SmartRow:
    name: str
    temp_c: str
    data_units: str
    detail: str


def sample_smart() -> list[SmartRow]:
    rows: list[SmartRow] = []
    nvme = "/sys/class/nvme"
    try:
        devices = os.listdir(nvme)
    except OSError:
        return rows
    for name in devices:
        d = os.path.join(nvme, name)
        temp = ""
        hwmon = os.path.join(d, "device", "hwmon")
        try:
            chips = os.listdir(hwmon)
        except OSError:
            chips = []
        for chip in chips:
            tfile = os.path.join(hwmon, chip, "temp1_input")
            try:
                with open(tfile, encoding="utf-8") as fh:
                    milli = float(fh.read().strip())
                temp = f"{milli / 1000:.0f} °C" if milli > 200 else f"{milli:.0f} °C"
                break
            except (OSError, ValueError):
                continue
        model = name
        try:
            with open(os.path.join(d, "model"), encoding="utf-8") as fh:
                model = fh.read().strip()
        except OSError:
            pass
        rows.append(SmartRow(name, temp, "", model))
    return rows
