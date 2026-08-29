from __future__ import annotations

import os
from hbomb.snapshot.types import GpuSnapshot, NpuSnapshot


def sample_gpu() -> GpuSnapshot:
    nv = _nvidia()
    if nv.available:
        return nv
    return _drm()


def _nvidia() -> GpuSnapshot:
    try:
        from pynvml import (
            nvmlInit,
            nvmlDeviceGetHandleByIndex,
            nvmlDeviceGetName,
            nvmlDeviceGetUtilizationRates,
            nvmlDeviceGetMemoryInfo,
            nvmlDeviceGetTemperature,
            nvmlDeviceGetClockInfo,
            NVML_TEMPERATURE_GPU,
            NVML_CLOCK_GRAPHICS,
        )
    except Exception:
        return GpuSnapshot()
    try:
        nvmlInit()
        h = nvmlDeviceGetHandleByIndex(0)
        name = nvmlDeviceGetName(h)
        if isinstance(name, bytes):
            name = name.decode("utf-8", "replace")
        util = nvmlDeviceGetUtilizationRates(h)
        mem = nvmlDeviceGetMemoryInfo(h)
        try:
            temp = float(nvmlDeviceGetTemperature(h, NVML_TEMPERATURE_GPU))
        except Exception:
            temp = 0.0
        try:
            clock = float(nvmlDeviceGetClockInfo(h, NVML_CLOCK_GRAPHICS))
        except Exception:
            clock = 0.0
        return GpuSnapshot(
            name=str(name),
            util=util.gpu / 100.0,
            vram_used=int(mem.used),
            vram_total=int(mem.total),
            temp_c=temp,
            clock_mhz=clock,
            available=True,
        )
    except Exception:
        return GpuSnapshot()


def _drm() -> GpuSnapshot:
    base = "/sys/class/drm"
    try:
        cards = sorted(n for n in os.listdir(base) if n.startswith("card") and n[4:].isdigit())
    except OSError:
        return GpuSnapshot()
    for card in cards:
        path = os.path.join(base, card, "device")
        name = card
        try:
            with open(os.path.join(path, "vendor"), "r", encoding="utf-8") as fh:
                vendor = fh.read().strip()
            name = f"DRM {card} ({vendor})"
        except OSError:
            pass
        busy = 0.0
        for cand in ("gpu_busy_percent",):
            try:
                with open(os.path.join(path, cand), "r", encoding="utf-8") as fh:
                    busy = float(fh.read().strip()) / 100.0
            except (OSError, ValueError):
                continue
        vram_used = vram_total = 0
        try:
            with open(os.path.join(path, "mem_info_vram_used"), "r", encoding="utf-8") as fh:
                vram_used = int(fh.read().strip())
            with open(os.path.join(path, "mem_info_vram_total"), "r", encoding="utf-8") as fh:
                vram_total = int(fh.read().strip())
        except (OSError, ValueError):
            pass
        if busy or vram_total:
            return GpuSnapshot(name=name, util=busy, vram_used=vram_used, vram_total=vram_total, available=True)
    return GpuSnapshot()


def sample_npu() -> NpuSnapshot:
    for path in (
        "/sys/class/accel/accel0/device/npu_busy_percent",
        "/sys/class/drm/card0/device/npu_busy_percent",
    ):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return NpuSnapshot(util=float(fh.read().strip()) / 100.0, available=True)
        except (OSError, ValueError):
            continue
    return NpuSnapshot()
