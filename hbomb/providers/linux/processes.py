from __future__ import annotations

import os
import pwd
from dataclasses import dataclass, field

from hbomb.snapshot.types import ProcessRow

_CLK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
_PAGE = os.sysconf("SC_PAGESIZE") if hasattr(os, "sysconf") else 4096

_STATE = {
    "R": "Running",
    "S": "Sleeping",
    "D": "Disk sleep",
    "Z": "Zombie",
    "T": "Stopped",
    "t": "Tracing",
    "I": "Idle",
}


@dataclass
class _PrevProc:
    utime: int = 0
    stime: int = 0
    read_bytes: int = 0
    write_bytes: int = 0
    wall: float = 0.0


class ProcessSampler:
    def __init__(self) -> None:
        self._prev: dict[int, _PrevProc] = {}
        self._uid_cache: dict[int, str] = {}

    def _user(self, uid: int) -> str:
        name = self._uid_cache.get(uid)
        if name is None:
            try:
                name = pwd.getpwuid(uid).pw_name
            except KeyError:
                name = str(uid)
            self._uid_cache[uid] = name
        return name

    def sample(self, now: float, hide: frozenset[int] | None = None) -> list[ProcessRow]:
        hide = hide or frozenset()
        rows: list[ProcessRow] = []
        seen: set[int] = set()
        try:
            pids = [int(n) for n in os.listdir("/proc") if n.isdigit()]
        except OSError:
            return []
        by_ppid: dict[int, list[int]] = {}
        for pid in pids:
            try:
                row = self._one(pid, now)
            except (OSError, ValueError, IndexError):
                continue
            if row is None:
                continue
            rows.append(row)
            seen.add(pid)
            by_ppid.setdefault(row.ppid, []).append(pid)
        for row in rows:
            row.children = by_ppid.get(row.pid, [])
        self._prev = {p.pid: self._prev[p.pid] for p in rows if p.pid in self._prev}
        return rows

    def _one(self, pid: int, now: float) -> ProcessRow | None:
        stat_path = f"/proc/{pid}/stat"
        with open(stat_path, "r", encoding="utf-8", errors="replace") as fh:
            stat = fh.read()
        rparen = stat.rfind(")")
        lparen = stat.find("(")
        name = stat[lparen + 1 : rparen]
        rest = stat[rparen + 2 :].split()
        state = rest[0]
        ppid = int(rest[1])
        utime = int(rest[11])
        stime = int(rest[12])
        nice = int(rest[16])
        threads = int(rest[17])
        vsize = int(rest[20])
        rss_pages = int(rest[21])
        uid = 0
        status_name = name
        try:
            with open(f"/proc/{pid}/status", "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("Uid:"):
                        uid = int(line.split()[1])
                    elif line.startswith("Name:"):
                        status_name = line.split(":", 1)[1].strip()
        except OSError:
            pass
        read_b = write_b = 0
        try:
            with open(f"/proc/{pid}/io", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("read_bytes:"):
                        read_b = int(line.split()[1])
                    elif line.startswith("write_bytes:"):
                        write_b = int(line.split()[1])
        except OSError:
            pass
        fds = 0
        try:
            fds = len(os.listdir(f"/proc/{pid}/fd"))
        except OSError:
            pass
        cmd = ""
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                raw = fh.read().replace(b"\x00", b" ").strip()
                cmd = raw.decode("utf-8", "replace")
        except OSError:
            pass
        prev = self._prev.get(pid, _PrevProc(utime=utime, stime=stime, read_bytes=read_b, write_bytes=write_b, wall=now))
        dt = max(1e-6, now - prev.wall)
        cpu = ((utime + stime) - (prev.utime + prev.stime)) / _CLK / dt
        r_bps = max(0.0, (read_b - prev.read_bytes) / dt)
        w_bps = max(0.0, (write_b - prev.write_bytes) / dt)
        self._prev[pid] = _PrevProc(utime, stime, read_b, write_b, now)
        return ProcessRow(
            pid=pid,
            ppid=ppid,
            name=status_name or name,
            user=self._user(uid),
            status=_STATE.get(state, state),
            cpu=max(0.0, cpu),
            mem_bytes=rss_pages * _PAGE,
            disk_read_bps=r_bps,
            disk_write_bps=w_bps,
            threads=threads,
            virt_bytes=vsize,
            fds=fds,
            nice=nice,
            command=cmd or name,
        )


def descendants(rows: list[ProcessRow], pid: int) -> list[int]:
    by_pid = {r.pid: r for r in rows}
    out: list[int] = []
    stack = list(by_pid.get(pid).children) if pid in by_pid else []
    seen = {pid}
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        out.append(cur)
        child = by_pid.get(cur)
        if child:
            stack.extend(child.children)
    return out


def child_pids_of(pid: int) -> set[int]:
    """Best-effort children via /proc, used to hide H-Bomb itself."""
    found = {pid}
    try:
        pids = [int(n) for n in os.listdir("/proc") if n.isdigit()]
    except OSError:
        return found
    changed = True
    ppid_of: dict[int, int] = {}
    for p in pids:
        try:
            with open(f"/proc/{p}/stat", "r", encoding="utf-8", errors="replace") as fh:
                st = fh.read()
            rest = st[st.rfind(")") + 2 :].split()
            ppid_of[p] = int(rest[1])
        except (OSError, ValueError, IndexError):
            continue
    while changed:
        changed = False
        for p, pp in ppid_of.items():
            if pp in found and p not in found:
                found.add(p)
                changed = True
    return found
