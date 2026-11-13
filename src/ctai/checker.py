"""Rule-level validation and objective computation.

The checker is the single source of truth for "is this plan legal" and "how good is it". It is
deliberately independent from any algorithm: algorithms may call it through
:class:`ctai.submitter.SolutionSubmitter`, but they cannot change it.

Rules enforced (``docs/rules.md`` Sections 3, 4 and 8):

1. every route starts and ends at depot 0;
2. every customer is served exactly once;
3. at most ``vehicle_count`` vehicles are used, each id in ``1..vehicle_count``;
4. the load of a vehicle never exceeds ``vehicle_capacity_kg``;
5. service at a customer starts inside its closed time window (an early arrival waits);
6. the makespan is the latest return to the depot, distance is the sum over all routes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .problem import Problem, TOL


@dataclass(frozen=True)
class RouteReport:
    """Per-vehicle outcome, kept for reporting and plotting."""

    vehicle_id: int
    stops: tuple[int, ...]
    load_kg: float
    distance_km: float
    completion_min: float
    service_start: tuple[float, ...]
    feasible: bool


@dataclass(frozen=True)
class Evaluation:
    """Full evaluation of one candidate plan."""

    feasible: bool
    makespan_min: float | None
    total_distance_km: float | None
    routes: tuple[RouteReport, ...]
    errors: tuple[str, ...]

    @property
    def score(self) -> tuple[float, float]:
        """Lexicographic key: makespan, then total distance."""
        if not self.feasible:
            return (float("inf"), float("inf"))
        return (float(self.makespan_min or 0.0), float(self.total_distance_km or 0.0))

    def as_dict(self) -> dict:
        return {
            "feasible": self.feasible,
            "makespan_min": self.makespan_min,
            "total_distance_km": self.total_distance_km,
            "validation_errors": list(self.errors),
            "routes": [
                {
                    "vehicle_id": r.vehicle_id,
                    "stops": list(r.stops),
                    "load_kg": round(r.load_kg, 6),
                    "distance_km": round(r.distance_km, 6),
                    "completion_min": round(r.completion_min, 6),
                }
                for r in self.routes
            ],
        }


def _as_dict(route) -> dict:
    """Accept either ``{"vehicle_id": .., "stops": [..]}`` or a 2-tuple ``(id, stops)``."""
    if isinstance(route, dict):
        return {"vehicle_id": route.get("vehicle_id"), "stops": list(route.get("stops", []))}
    vehicle_id, stops = route
    return {"vehicle_id": vehicle_id, "stops": list(stops)}


def evaluate_routes(
    instance: dict,
    routes: list,
    problem: Problem | None = None,
) -> Evaluation:
    """Validate a plan and compute its objectives.

    Args:
        instance: the scenario the plan refers to.
        routes: one entry per used vehicle, ``{"vehicle_id": int, "stops": [0, ... , 0]}``.
        problem: optional preprocessed scenario, to avoid rebuilding the matrix.

    Returns:
        An :class:`Evaluation`; ``feasible`` is ``False`` whenever any rule is broken, and
        ``makespan_min`` / ``total_distance_km`` are then ``None`` so a broken plan can never be
        mistaken for a good one.
    """
    problem = problem or Problem(instance)
    routes = [_as_dict(r) for r in routes]
    errors: list[str] = []
    reports: list[RouteReport] = []

    expected_ids = set(range(1, instance["customer_count"] + 1))
    seen: list[int] = []
    used_vehicle_ids: list[int] = []

    for route in routes:
        vehicle_id = route["vehicle_id"]
        stops = route["stops"]
        if not isinstance(vehicle_id, int):
            errors.append(f"vehicle_id {vehicle_id!r} is not an integer")
            continue
        used_vehicle_ids.append(vehicle_id)
        if not 1 <= vehicle_id <= problem.vehicle_count:
            errors.append(f"vehicle_id {vehicle_id} outside 1..{problem.vehicle_count}")

        if len(stops) < 2 or stops[0] != 0 or stops[-1] != 0:
            errors.append(f"vehicle {vehicle_id}: route must start and end at depot 0")
            continue
        unknown = [s for s in stops[1:-1] if s not in expected_ids]
        if unknown:
            errors.append(f"vehicle {vehicle_id}: unknown customer ids {sorted(set(unknown))}")
            continue

        seen.extend(stops[1:-1])
        stats = problem.evaluate_path(stops)
        reports.append(
            RouteReport(
                vehicle_id=vehicle_id,
                stops=tuple(stops),
                load_kg=stats.load_kg,
                distance_km=stats.distance_km,
                completion_min=stats.completion_min,
                service_start=stats.service_start,
                feasible=stats.feasible,
            )
        )
        if stats.load_kg > problem.capacity + TOL:
            errors.append(
                f"vehicle {vehicle_id}: load {stats.load_kg:.1f} kg exceeds capacity "
                f"{problem.capacity:.1f} kg"
            )
        if stats.lateness_min > TOL:
            errors.append(
                f"vehicle {vehicle_id}: time-window violation of {stats.lateness_min:.2f} min"
            )

    if len(set(used_vehicle_ids)) != len(used_vehicle_ids):
        errors.append("the same vehicle_id appears in more than one route")

    served = set(seen)
    missing = sorted(expected_ids - served)
    duplicated = sorted({c for c in seen if seen.count(c) > 1})
    if missing:
        errors.append(f"customers not served: {missing}")
    if duplicated:
        errors.append(f"customers served more than once: {duplicated}")

    feasible = (
        not errors
        and len(seen) == len(expected_ids)
        and all(r.feasible for r in reports)
    )
    if not feasible:
        return Evaluation(False, None, None, tuple(reports), tuple(errors))

    makespan = max((r.completion_min for r in reports), default=0.0)
    distance = sum(r.distance_km for r in reports)
    return Evaluation(True, makespan, distance, tuple(reports), ())


def renders_as_table(evaluation: Evaluation) -> str:
    """Compact human-readable summary of one plan."""
    if not evaluation.feasible:
        lines = ["infeasible plan:"]
        lines += [f"  - {e}" for e in evaluation.errors] or ["  - (no diagnostic)"]
        return "\n".join(lines)

    rows = ["vehicle  stops                          load(kg)  dist(km)  done(min)"]
    for r in evaluation.routes:
        stops = " ".join(str(s) for s in r.stops)
        rows.append(
            f"{r.vehicle_id:>7}  {stops:<30} {r.load_kg:>8.1f} {r.distance_km:>9.2f} "
            f"{r.completion_min:>10.2f}"
        )
    rows.append(
        f"makespan {evaluation.makespan_min:.2f} min, "
        f"total distance {evaluation.total_distance_km:.2f} km"
    )
    return "\n".join(rows)
