from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProviderHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class CpuUtilization:
    """Share of non-idle time over the sample window. Values are 0..1."""

    total: float
    user: float
    kernel: float
    nice: float = 0.0
    irq: float = 0.0
    steal: float = 0.0


@dataclass
class LogicalCore:
    index: int
    util: CpuUtilization
    freq_ghz: float = 0.0
    is_efficiency: bool = False
    numa_node: int = 0


@dataclass
class CpuSnapshot:
    overall: CpuUtilization
    cores: list[LogicalCore]
    freq_ghz: float
    base_ghz: float = 0.0
    sockets: int = 1
    physical_cores: int = 0
    logical_processors: int = 0
    caches: str = ""
    virtualization: str = ""
    governor: str = ""
    freq_driver: str = ""
    uptime_s: float = 0.0
    process_count: int = 0
    thread_count: int = 0
    model_name: str = ""


@dataclass
class MemorySnapshot:
    total_bytes: int = 0
    available_bytes: int = 0
    application_bytes: int = 0
    wired_bytes: int = 0
    compressed_bytes: int = 0
    cached_bytes: int = 0
    committed_bytes: int = 0
    swap_used_bytes: int = 0
    swap_total_bytes: int = 0
    occupied_bytes: int = 0
    expensive_bytes: int = 0
    psi_avg10: float = 0.0
    psi_avg60: float = 0.0
    psi_avg300: float = 0.0
    psi_some: float = 0.0
    dimm_summary: str = ""

    @property
    def used_ratio(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(1.0, self.occupied_bytes / self.total_bytes)


@dataclass
class GpuSnapshot:
    name: str = ""
    util: float = 0.0
    vram_used: int = 0
    vram_total: int = 0
    temp_c: float = 0.0
    clock_mhz: float = 0.0
    available: bool = False


@dataclass
class NpuSnapshot:
    util: float = 0.0
    available: bool = False


@dataclass
class DiskDevice:
    name: str
    read_bps: float = 0.0
    write_bps: float = 0.0
    busy: float = 0.0
    size_bytes: int = 0
    used_bytes: int = 0
    mount: str = ""


@dataclass
class DiskSnapshot:
    devices: list[DiskDevice] = field(default_factory=list)
    read_bps: float = 0.0
    write_bps: float = 0.0
    busy: float = 0.0


@dataclass
class NetIface:
    name: str
    rx_bps: float = 0.0
    tx_bps: float = 0.0
    rx_bytes: int = 0
    tx_bytes: int = 0
    speed_mbps: float = 0.0
    operstate: str = ""
    is_virtual: bool = False


@dataclass
class NetSnapshot:
    ifaces: list[NetIface] = field(default_factory=list)
    rx_bps: float = 0.0
    tx_bps: float = 0.0
    session_rx: int = 0
    session_tx: int = 0
    link_speed_mbps: float = 0.0


@dataclass
class EnergySnapshot:
    watts: Optional[float] = None
    governor: str = ""
    power_state: str = ""
    battery_pct: Optional[float] = None


@dataclass
class ThermalSensor:
    name: str
    temp_c: float
    kind: str = "pickup"


@dataclass
class ThermalSnapshot:
    hotspot_c: float = 0.0
    sensors: list[ThermalSensor] = field(default_factory=list)


@dataclass
class ProcessRow:
    pid: int
    ppid: int
    name: str
    user: str
    status: str
    cpu: float
    mem_bytes: int
    disk_read_bps: float
    disk_write_bps: float
    threads: int
    virt_bytes: int
    fds: int
    nice: int
    command: str
    gpu: float = 0.0
    energy: Optional[float] = None
    children: list[int] = field(default_factory=list)


@dataclass
class ProviderStatus:
    name: str
    health: ProviderHealth
    detail: str = ""


@dataclass
class Snapshot:
    generation: int
    timestamp: float
    cpu: CpuSnapshot
    memory: MemorySnapshot
    gpu: GpuSnapshot
    npu: NpuSnapshot
    disk: DiskSnapshot
    net: NetSnapshot
    energy: EnergySnapshot
    thermals: ThermalSnapshot
    processes: list[ProcessRow]
    providers: list[ProviderStatus]
    app_pids: frozenset[int] = field(default_factory=frozenset)

    def health(self) -> ProviderHealth:
        core = {p.name: p for p in self.providers if p.name in ("cpu", "memory", "processes")}
        if not core:
            return ProviderHealth.UNAVAILABLE
        if any(p.health == ProviderHealth.UNAVAILABLE for p in core.values()):
            return ProviderHealth.DEGRADED
        if any(p.health == ProviderHealth.DEGRADED for p in core.values()):
            return ProviderHealth.DEGRADED
        return ProviderHealth.HEALTHY

    def visible_processes(self, include_self: bool) -> list[ProcessRow]:
        if include_self:
            return self.processes
        hidden = self.app_pids
        return [p for p in self.processes if p.pid not in hidden]
