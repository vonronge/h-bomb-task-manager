from __future__ import annotations

from dataclasses import dataclass, field
import math


@dataclass
class Sample:
    t: float
    value: float


class LogHistory:
    """Dense recent edge, coarsened tail (¼, ⅛, ⅛… style).

    The right edge of a plot is the newest samples at full rate. Older
    buckets hold averaged values so an afternoon of 60 Hz data does not
    grow toward a gigabyte ring buffer.
    """

    def __init__(self, dense_cap: int = 240, max_levels: int = 12) -> None:
        self.dense_cap = dense_cap
        self.max_levels = max_levels
        self._dense: list[Sample] = []
        self._levels: list[list[Sample]] = [[] for _ in range(max_levels)]
        self._pending: list[list[Sample]] = [[] for _ in range(max_levels)]

    def push(self, t: float, value: float) -> None:
        self._dense.append(Sample(t, value))
        overflow = len(self._dense) - self.dense_cap
        if overflow <= 0:
            return
        spilled = self._dense[:overflow]
        del self._dense[:overflow]
        self._ingest(0, spilled)

    def _ingest(self, level: int, samples: list[Sample]) -> None:
        if level >= self.max_levels or not samples:
            return
        self._pending[level].extend(samples)
        while len(self._pending[level]) >= 4:
            group = self._pending[level][:4]
            del self._pending[level][:4]
            t = group[-1].t
            v = sum(s.value for s in group) / 4.0
            merged = Sample(t, v)
            bucket = self._levels[level]
            bucket.append(merged)
            if len(bucket) > 64:
                spill = bucket[: max(1, len(bucket) - 48)]
                del bucket[: len(spill)]
                self._ingest(level + 1, spill)

    def series(self) -> list[Sample]:
        out: list[Sample] = []
        for level in range(self.max_levels - 1, -1, -1):
            out.extend(self._levels[level])
            out.extend(self._pending[level])
        out.extend(self._dense)
        out.sort(key=lambda s: s.t)
        return out

    def values(self) -> list[float]:
        return [s.value for s in self.series()]

    def clear(self) -> None:
        self._dense.clear()
        for i in range(self.max_levels):
            self._levels[i].clear()
            self._pending[i].clear()


class HistoryBank:
    def __init__(self) -> None:
        self._series: dict[str, LogHistory] = {}

    def push(self, name: str, t: float, value: float) -> None:
        hist = self._series.get(name)
        if hist is None:
            hist = LogHistory()
            self._series[name] = hist
        hist.push(t, value)

    def get(self, name: str) -> LogHistory:
        hist = self._series.get(name)
        if hist is None:
            hist = LogHistory()
            self._series[name] = hist
        return hist

    def names(self) -> list[str]:
        return list(self._series)


def ease(current: float, target: float, dt: float, tau: float = 0.12) -> float:
    """First-order meter ballistics. Needle has mass; sample rate does not."""
    if tau <= 0:
        return target
    k = 1.0 - math.exp(-dt / tau)
    return current + (target - current) * k


def log_time_fraction(t: float, t_min: float, t_max: float) -> float:
    """Map a timestamp to 0..1 for plotting. 1.0 is newest (right edge).

    Uses log1p on elapsed time since t_min so recent seconds occupy more
    horizontal space than older history on the left.
    """
    if t_max <= t_min:
        return 1.0
    span = t_max - t_min
    elapsed = max(0.0, min(span, t - t_min))
    denom = math.log1p(span)
    if denom <= 0:
        return 1.0
    return math.log1p(elapsed) / denom


def age_from_fraction(frac: float, span: float) -> float:
    """Horizontal fraction -> seconds before t_max (for crosshair lookup)."""
    frac = max(0.0, min(1.0, frac))
    elapsed = math.expm1(frac * math.log1p(max(0.0, span)))
    return max(0.0, span - elapsed)


def log_grid_ages(span: float) -> list[float]:
    """Seconds-before-now tick marks for vertical grid lines (denser on the right)."""
    if span <= 0:
        return []
    marks = [0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1800, 3600, 7200, 14400, 28800]
    return [a for a in marks if a < span * 0.995]
