from __future__ import annotations

import os
from hbomb.providers.linux import cpu as cpu_mod
from hbomb.providers.linux import memory as memory_mod
from hbomb.providers.linux import processes as proc_mod
from hbomb.providers.linux.disknet import DiskNetSampler
from hbomb.providers.linux.gpu import sample_gpu, sample_npu
from hbomb.providers.linux.sensors import sample_energy, sample_thermals
from hbomb.snapshot.types import (
    Snapshot,
    ProviderStatus,
    ProviderHealth,
)


def _ok(name: str, ok: bool, detail: str = "") -> ProviderStatus:
    return ProviderStatus(
        name,
        ProviderHealth.HEALTHY if ok else ProviderHealth.UNAVAILABLE,
        detail,
    )


class LinuxCollector:
    def __init__(self) -> None:
        self.cpu = cpu_mod.CpuSampler()
        self.procs = proc_mod.ProcessSampler()
        self.disknet = DiskNetSampler()
        self._session_rx0: int | None = None
        self._session_tx0: int | None = None
        self._last_rows: list = []
        self._last_gpu = None
        self._last_npu = None
        self._last_therm = None

    def collect(
        self,
        generation: int,
        now: float,
        app_pids: frozenset[int],
        sample_procs: bool = True,
        sample_heavy: bool = True,
    ) -> Snapshot:
        providers: list[ProviderStatus] = []
        if sample_procs or not self._last_rows:
            try:
                rows = self.procs.sample(now)
                self._last_rows = rows
                providers.append(_ok("processes", True, f"{len(rows)}"))
            except OSError as exc:
                rows = self._last_rows
                providers.append(_ok("processes", False, str(exc)))
        else:
            rows = self._last_rows
            providers.append(_ok("processes", True, f"{len(rows)}"))
        threads = sum(r.threads for r in rows)
        try:
            cpu = self.cpu.sample(len(rows), threads)
            providers.append(_ok("cpu", True, cpu.model_name))
        except OSError as exc:
            cpu = self.cpu.sample(len(rows), threads)
            providers.append(_ok("cpu", False, str(exc)))
        try:
            mem = memory_mod.sample_memory()
            providers.append(_ok("memory", True))
        except OSError as exc:
            from hbomb.snapshot.types import MemorySnapshot

            mem = MemorySnapshot()
            providers.append(_ok("memory", False, str(exc)))
        if sample_heavy or self._last_gpu is None:
            gpu = sample_gpu()
            npu = sample_npu()
            therm = sample_thermals()
            self._last_gpu, self._last_npu, self._last_therm = gpu, npu, therm
        else:
            gpu, npu, therm = self._last_gpu, self._last_npu, self._last_therm
        providers.append(_ok("gpu", gpu.available, gpu.name))
        providers.append(
            ProviderStatus(
                "npu",
                ProviderHealth.HEALTHY if npu.available else ProviderHealth.UNAVAILABLE,
                "" if npu.available else "not published",
            )
        )
        try:
            disk, net = self.disknet.sample(now)
            providers.append(_ok("disk", True))
            providers.append(_ok("net", True))
        except OSError as exc:
            from hbomb.snapshot.types import DiskSnapshot, NetSnapshot

            disk, net = DiskSnapshot(), NetSnapshot()
            providers.append(_ok("disk", False, str(exc)))
            providers.append(_ok("net", False, str(exc)))
        if self._session_rx0 is None:
            self._session_rx0 = sum(i.rx_bytes for i in net.ifaces)
            self._session_tx0 = sum(i.tx_bytes for i in net.ifaces)
        net.session_rx = max(0, sum(i.rx_bytes for i in net.ifaces) - (self._session_rx0 or 0))
        net.session_tx = max(0, sum(i.tx_bytes for i in net.ifaces) - (self._session_tx0 or 0))
        energy = sample_energy(cpu.governor)
        providers.append(
            ProviderStatus(
                "energy",
                ProviderHealth.HEALTHY if energy.watts is not None else ProviderHealth.UNAVAILABLE,
                "" if energy.watts is not None else "RAPL unavailable",
            )
        )
        providers.append(_ok("thermals", bool(therm.sensors)))
        return Snapshot(
            generation=generation,
            timestamp=now,
            cpu=cpu,
            memory=mem,
            gpu=gpu,
            npu=npu,
            disk=disk,
            net=net,
            energy=energy,
            thermals=therm,
            processes=rows,
            providers=providers,
            app_pids=app_pids,
        )
