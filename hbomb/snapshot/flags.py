from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureFlags:
    power_freq: bool = True
    connections: bool = True
    installed_apps: bool = True
    disk_space: bool = True
    benchmarks: bool = True
    flight_recorder: bool = True
    smart: bool = True
    apple_silicon: bool = False

    def enabled(self, name: str) -> bool:
        return bool(getattr(self, name, False))
