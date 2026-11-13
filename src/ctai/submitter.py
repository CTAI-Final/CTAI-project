"""The submission channel between an algorithm and the test harness.

An algorithm never returns a plan and never measures itself. It calls ``submit`` as often as it
likes; the harness keeps the best feasible plan it has seen, validates everything, and builds the
final result record. That is what makes the two stopping modes interchangeable: if a run is cut
off in the middle of a construction, the last submitted plan is still reported.

See ``docs/interface.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .checker import Evaluation, evaluate_routes
from .problem import Problem


@dataclass
class SubmissionLog:
    submissions: int = 0
    rejections: int = 0
    improvements: int = 0
    first_feasible_at: int | None = None


class SolutionSubmitter:
    """Collects candidate plans and keeps the best feasible one."""

    def __init__(self, instance: dict, problem: Problem | None = None) -> None:
        self.instance = instance
        self.problem = problem or Problem(instance)
        self.best_routes: list[dict] | None = None
        self.best_evaluation: Evaluation | None = None
        self.log = SubmissionLog()

    # -- algorithm-facing API ---------------------------------------------------------------
    def submit(self, routes: list) -> dict:
        """Validate a candidate plan and keep it if it beats the incumbent.

        Args:
            routes: ``[{"vehicle_id": 1, "stops": [0, 4, 2, 0]}, ...]``. Empty routes may be
                omitted; a vehicle that is not used deserves no entry.

        Returns:
            The evaluation of *this* candidate as a plain dict: ``feasible``,
            ``makespan_min``, ``total_distance_km``, ``validation_errors``.
        """
        self.log.submissions += 1
        evaluation = evaluate_routes(self.instance, routes, self.problem)

        if not evaluation.feasible:
            self.log.rejections += 1
            return evaluation.as_dict()

        if self.log.first_feasible_at is None:
            self.log.first_feasible_at = self.log.submissions

        if self.best_evaluation is None or evaluation.score < self.best_evaluation.score:
            self.best_evaluation = evaluation
            self.best_routes = [
                {"vehicle_id": r.vehicle_id, "stops": list(r.stops)} for r in evaluation.routes
            ]
            self.log.improvements += 1
        return evaluation.as_dict()

    @property
    def best_score(self) -> tuple[float, float]:
        if self.best_evaluation is None:
            return (float("inf"), float("inf"))
        return self.best_evaluation.score

    # -- harness-facing API -----------------------------------------------------------------
    def to_result(
        self,
        termination: str,
        runtime_sec: float | None = None,
        work_done: int | None = None,
        error: str | None = None,
    ) -> dict:
        """Build the run record. Never raises, even if no feasible plan was produced."""
        evaluation = self.best_evaluation
        return {
            "feasible": bool(evaluation and evaluation.feasible),
            "makespan_min": evaluation.makespan_min if evaluation else None,
            "total_distance_km": evaluation.total_distance_km if evaluation else None,
            "routes": self.best_routes or [],
            "validation_errors": list(evaluation.errors) if evaluation else ["no feasible plan submitted"],
            "termination": termination,
            "error": error,
            "runtime_sec": round(runtime_sec, 4) if runtime_sec is not None else None,
            "work_done": work_done,
            "submissions": self.log.submissions,
            "rejections": self.log.rejections,
            "improvements": self.log.improvements,
        }


def parse_routes(payload: Sequence) -> list[dict]:
    """Normalise ``[[1, [0, 2, 0]]]`` or ``[{"vehicle_id": 1, ...}]`` to the dict form."""
    routes = []
    for item in payload:
        if isinstance(item, dict):
            routes.append({"vehicle_id": item["vehicle_id"], "stops": list(item["stops"])})
        else:
            vehicle_id, stops = item
            routes.append({"vehicle_id": vehicle_id, "stops": list(stops)})
    return routes
