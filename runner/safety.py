"""Safety limit and run-status recording (rules Sections 5 and 8).

- The scale group may define a separate safety limit (exact seconds pending review; it does not
  default to 30 seconds);
- Reaching the safety limit, or exiting abnormally before the required work is complete, marks
  the run as not completed and saves the actual work done and the elapsed time;
- The safety-limit time must not be used as a complete run time;
- termination values: completed / timeout / error / safety_timeout.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunStatus:
    """Status of a single run."""

    termination: str = "completed"       # completed/timeout/error/safety_timeout
    work_done: int | None = None         # work actually completed
    work_budget: int | None = None       # target work
    safety_limit_sec: float | None = None
    error_message: str | None = None

    @property
    def work_completed(self) -> bool:
        """Whether the required work was fully executed (independent of feasibility)."""
        return (self.termination == "completed"
                and self.work_done is not None
                and self.work_budget is not None
                and self.work_done >= self.work_budget)

    def hit_safety_limit(self, elapsed_sec: float) -> bool:
        if self.safety_limit_sec is None:
            return False
        return elapsed_sec >= self.safety_limit_sec


def mark_safety_timeout(status: RunStatus, meter_total: int) -> RunStatus:
    status.termination = "safety_timeout"
    status.work_done = meter_total
    return status


def mark_error(status: RunStatus, exc: Exception, meter_total: int) -> RunStatus:
    status.termination = "error"
    status.work_done = meter_total
    status.error_message = f"{type(exc).__name__}: {exc}"
    return status
