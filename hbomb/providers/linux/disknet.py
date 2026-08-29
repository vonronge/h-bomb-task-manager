from __future__ import annotations

import os
from dataclasses import dataclass

from hbomb.snapshot.types import DiskDevice, DiskSnapshot, NetIface, NetSnapshot


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


@dataclass
class _DiskPrev:
    read_sectors: int = 0
    write_sectors: int = 0
    io_ticks: int = 0
    wall: float = 0.0


@dataclass
class _NetPrev:
    rx: int = 0
    tx: int = 0
    wall: float = 0.0


_SKIP_DISK = {"loop", "ram", "sr"}
_SKIP_NET_PREFIX = ("lo", "docker", "veth", "br-", "virbr", "tun", "tap", "wg")


class DiskNetSampler:
    def __init__(self) -> None:
        self._disk: dict[str, _DiskPrev] = {}
        self._net: dict[str, _NetPrev] = {}

    def sample(self, now: float) -> tuple[DiskSnapshot, NetSnapshot]:
        return self._disks(now), self._nets(now)

    def _disks(self, now: float) -> DiskSnapshot:
        devices: list[DiskDevice] = []
        try:
            text = _read("/proc/diskstats")
        except OSError:
            return DiskSnapshot()
        for line in text.splitlines():
            parts = line.split()
            if len(parts) < 14:
                continue
            name = parts[2]
            if any(name.startswith(p) for p in _SKIP_DISK):
                continue
            # skip partitions (sda1) when we have the parent; keep nvme0n1 not nvme0n1p1
            if name[-1].isdigit() and not name.startswith("nvme"):
                continue
            if "p" in name and name.split("p")[-1].isdigit() and name.startswith("nvme"):
                continue
            try:
                read_sect = int(parts[5])
                write_sect = int(parts[9])
                io_ticks = int(parts[12])
            except ValueError:
                continue
            prev = self._disk.get(name, _DiskPrev(read_sect, write_sect, io_ticks, now))
            dt = max(1e-6, now - prev.wall)
            r_bps = max(0.0, (read_sect - prev.read_sectors) * 512 / dt)
            w_bps = max(0.0, (write_sect - prev.write_sectors) * 512 / dt)
            busy = min(1.0, max(0.0, (io_ticks - prev.io_ticks) / (dt * 1000.0)))
            self._disk[name] = _DiskPrev(read_sect, write_sect, io_ticks, now)
            size = _block_size(name)
            used, mount = _mount_for(name)
            devices.append(
                DiskDevice(
                    name=name,
                    read_bps=r_bps,
                    write_bps=w_bps,
                    busy=busy,
                    size_bytes=size,
                    used_bytes=used,
                    mount=mount,
                )
            )
        tr = sum(d.read_bps for d in devices)
        tw = sum(d.write_bps for d in devices)
        busy = max((d.busy for d in devices), default=0.0)
        return DiskSnapshot(devices=devices, read_bps=tr, write_bps=tw, busy=busy)

    def _nets(self, now: float) -> NetSnapshot:
        ifaces: list[NetIface] = []
        try:
            text = _read("/proc/net/dev")
        except OSError:
            return NetSnapshot()
        for line in text.splitlines()[2:]:
            if ":" not in line:
                continue
            name, rest = line.split(":", 1)
            name = name.strip()
            nums = rest.split()
            if len(nums) < 9:
                continue
            rx, tx = int(nums[0]), int(nums[8])
            virtual = name.startswith(_SKIP_NET_PREFIX) or name == "lo"
            prev = self._net.get(name, _NetPrev(rx, tx, now))
            dt = max(1e-6, now - prev.wall)
            rx_bps = max(0.0, (rx - prev.rx) / dt)
            tx_bps = max(0.0, (tx - prev.tx) / dt)
            self._net[name] = _NetPrev(rx, tx, now)
            speed, oper = _link_info(name)
            ifaces.append(
                NetIface(
                    name=name,
                    rx_bps=rx_bps,
                    tx_bps=tx_bps,
                    rx_bytes=rx,
                    tx_bytes=tx,
                    speed_mbps=speed,
                    operstate=oper,
                    is_virtual=virtual,
                )
            )
        real = [i for i in ifaces if not i.is_virtual]
        use = real or ifaces
        return NetSnapshot(
            ifaces=ifaces,
            rx_bps=sum(i.rx_bps for i in use),
            tx_bps=sum(i.tx_bps for i in use),
            link_speed_mbps=max((i.speed_mbps for i in use), default=0.0),
        )


def _block_size(name: str) -> int:
    try:
        return int(_read(f"/sys/block/{name}/size").strip()) * 512
    except (OSError, ValueError):
        return 0


def _mount_for(name: str) -> tuple[int, str]:
    try:
        with open("/proc/self/mounts", "r", encoding="utf-8") as fh:
            mounts = fh.readlines()
    except OSError:
        return 0, ""
    best = ""
    for line in mounts:
        dev = line.split()[0]
        mp = line.split()[1] if len(line.split()) > 1 else ""
        if name in os.path.basename(dev) or dev.endswith(name):
            if mp == "/" or len(mp) < len(best) or not best:
                best = mp
    if not best:
        return 0, ""
    try:
        st = os.statvfs(best.replace("\\040", " "))
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        return used, best.replace("\\040", " ")
    except OSError:
        return 0, best


def _link_info(name: str) -> tuple[float, str]:
    oper = ""
    speed = 0.0
    try:
        oper = _read(f"/sys/class/net/{name}/operstate").strip()
    except OSError:
        pass
    try:
        speed = float(_read(f"/sys/class/net/{name}/speed").strip())
    except (OSError, ValueError):
        pass
    return speed, oper
