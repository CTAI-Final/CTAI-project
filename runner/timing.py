"""Timing boundary control (timing-boundary suggestion in rules Section 5).

- Input loading and common preprocessing (distance matrix, ...) finish **before** timing starts;
- The algorithm's own initialization, construction, search, and in-run solution submission
  overhead are **counted**;
- Final review, statistics and plotting are **not counted**;
- Preprocessing cost is recorded separately and explained in the theoretical analysis.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Timer:
    """Solver-stage timer, in seconds."""

    elapsed: float = 0.0
    _start: float | None = None
    records: list[float] = field(default_factory=list)

    def start(self) -> None:
        self._start = time.perf_counter()

    def stop(self) -> float:
        if self._start is not None:
            seg = time.perf_counter() - self._start
            self.elapsed += seg
            self.records.append(seg)
            self._start = None
        return self.elapsed

    @property
    def running(self) -> bool:
        return self._start is not None


@contextmanager
def measure(out: dict, key: str):
    """Accumulate the duration of a block into out[key] (seconds).

    Used to separate the preprocessing / solving / review stages.
    """
    t0 = time.perf_counter()
    try:
        yield
    finally:
        out[key] = out.get(key, 0.0) + (time.perf_counter() - t0)


def within_budget(timer: Timer, time_limit_sec: float) -> bool:
    """Performance mode: whether the 30-second budget is still available."""
    return timer.elapsed < time_limit_sec
