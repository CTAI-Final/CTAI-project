"""Timing, work counting and the safety ceiling.

The project compares algorithms under two different stopping rules, so the three concerns are
kept apart but share one object:

*time budget* (performance group)
    Wall-clock limit per run, 30 s in the formal experiment.
*fixed work* (scale group)
    A machine-independent amount of search work instead of seconds, so the comparison does not
    inherit the speed of one particular laptop.
*safety ceiling*
    A hard wall-clock limit that aborts a run which would otherwise hang the whole batch. It is
    not part of the measurement; it only protects the experiment.

Work units
----------
One unit is **one candidate solution evaluation** — one feasibility + cost check of a complete
plan or of a candidate insertion / move. Reading the matrix or computing an objective from
values already in memory is free. Every algorithm counts with the same unit, which is what makes
the fixed-work group comparable. ``docs/interface.md`` repeats this definition for implementers.
"""

from __future__ import annotations

import time

DEFAULT_TIME_LIMIT_SEC = 30.0
DEFAULT_SAFETY_LIMIT_SEC = 120.0


class SafetyLimitExceeded(RuntimeError):
    """Raised when a run passes its hard wall-clock ceiling."""


class Stopwatch:
    """Monotonic wall-clock stopwatch."""

    __slots__ = ("_start",)

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def reset(self) -> None:
        self._start = time.perf_counter()

    @property
    def elapsed_sec(self) -> float:
        return time.perf_counter() - self._start


class WorkMeter:
    """Counts work units; optionally bounded by a budget."""

    __slots__ = ("units", "budget")

    def __init__(self, budget: int | None = None) -> None:
        self.units = 0
        self.budget = budget

    def spend(self, units: int = 1) -> None:
        self.units += units

    @property
    def exhausted(self) -> bool:
        return self.budget is not None and self.units >= self.budget

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"WorkMeter(units={self.units}, budget={self.budget})"


class Budget:
    """Stopping rule shared by the runner and every algorithm.

    Algorithms poll :attr:`expired` (or call :meth:`check`) in their main loops and return when
    it is true; they never read the wall clock themselves, so a run is reproducible given the
    seed and the work budget.
    """

    def __init__(
        self,
        mode: str = "time_budget",
        time_limit_sec: float | None = None,
        work_budget: int | None = None,
        safety_limit_sec: float | None = None,
    ) -> None:
        if mode not in ("time_budget", "fixed_work"):
            raise ValueError(f"unknown mode '{mode}', expected 'time_budget' or 'fixed_work'")
        if mode == "time_budget" and time_limit_sec is None:
            time_limit_sec = DEFAULT_TIME_LIMIT_SEC
        if mode == "fixed_work" and work_budget is None:
            raise ValueError("fixed_work mode requires work_budget")

        self.mode = mode
        self.time_limit_sec = time_limit_sec
        self.work = WorkMeter(work_budget)
        self.clock = Stopwatch()
        if safety_limit_sec is None:
            safety_limit_sec = (
                max(4 * (time_limit_sec or 0.0), DEFAULT_SAFETY_LIMIT_SEC)
                if mode == "time_budget"
                else DEFAULT_SAFETY_LIMIT_SEC * 3
            )
        self.safety_limit_sec = safety_limit_sec
        self._stop_reason: str | None = None

    # -- accounting ------------------------------------------------------------------------
    def spend(self, units: int = 1) -> None:
        """Record work; never raises, poll :attr:`expired` instead."""
        self.work.spend(units)

    @property
    def work_done(self) -> int:
        return self.work.units

    @property
    def elapsed_sec(self) -> float:
        return self.clock.elapsed_sec

    def remaining_sec(self) -> float:
        if self.time_limit_sec is None:
            return float("inf")
        return max(0.0, self.time_limit_sec - self.clock.elapsed_sec)

    # -- stopping rule ---------------------------------------------------------------------
    def stop_reason(self) -> str | None:
        """``None`` while the run may continue, otherwise why it must stop."""
        if self._stop_reason is not None:
            return self._stop_reason
        if self.clock.elapsed_sec > self.safety_limit_sec:
            self._stop_reason = "safety_limit"
            raise SafetyLimitExceeded(
                f"run exceeded the {self.safety_limit_sec:.0f} s safety ceiling"
            )
        if self.mode == "time_budget" and self.time_limit_sec is not None:
            if self.clock.elapsed_sec >= self.time_limit_sec:
                self._stop_reason = "time_budget"
                return self._stop_reason
        if self.mode == "fixed_work" and self.work.exhausted:
            self._stop_reason = "work_budget"
            return self._stop_reason
        return None

    def expired(self) -> bool:
        return self.stop_reason() is not None

    def check(self) -> None:
        """Raise :class:`SafetyLimitExceeded` if the hard ceiling is passed."""
        self.stop_reason()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Budget(mode={self.mode}, time_limit={self.time_limit_sec}, "
            f"work={self.work.units}/{self.work.budget}, elapsed={self.elapsed_sec:.2f}s)"
        )
