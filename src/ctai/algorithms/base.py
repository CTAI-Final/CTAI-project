"""Shared building blocks for the three reference algorithms.

Only *infrastructure* lives here: a mutable plan with cached route statistics, the objective
key, and one construction heuristic. The search strategy itself is the part that each
implementer owns and that must be different between the three submissions — see
``docs/algorithms/``.

All three reference implementations deliberately share the same constructor (sequential cheapest
insertion). That keeps the comparison honest: any difference in solution quality comes from the
improvement strategy, not from a lucky start.
"""

from __future__ import annotations

from typing import Sequence

from ..budget import Budget
from ..problem import PathStats, Problem


class Plan:
    """A set of routes plus their cached stats.

    ``routes[i]`` is the stop sequence of vehicle ``i + 1``. An unused vehicle keeps ``[0, 0]``,
    which costs nothing and is valid (the plan simply uses fewer vehicles).
    """

    def __init__(self, problem: Problem, routes: list[list[int]] | None = None) -> None:
        self.problem = problem
        self.routes: list[list[int]] = routes if routes is not None else problem.empty_plan()
        self.stats: list[PathStats] = [problem.evaluate_path(r) for r in self.routes]

    # -- state ------------------------------------------------------------------------------
    def copy(self) -> Plan:
        clone = Plan.__new__(Plan)
        clone.problem = self.problem
        clone.routes = [list(r) for r in self.routes]
        clone.stats = list(self.stats)
        return clone

    def set_route(self, index: int, stops: list[int], stats: PathStats) -> None:
        self.routes[index] = stops
        self.stats[index] = stats

    def used_routes(self) -> list[int]:
        return [i for i, r in enumerate(self.routes) if len(r) > 2]

    # -- metrics ----------------------------------------------------------------------------
    @property
    def makespan(self) -> float:
        return max((s.completion_min for s in self.stats), default=0.0)

    @property
    def total_distance(self) -> float:
        return sum(s.distance_km for s in self.stats)

    @property
    def feasible(self) -> bool:
        return all(s.feasible for s in self.stats)

    def objective(self) -> tuple[float, float]:
        """Lexicographic key: makespan first, total distance second.

        An infeasible plan is ranked after every feasible one, so a search can never "improve"
        into a broken plan.
        """
        if not self.feasible:
            return (float("inf"), float("inf"))
        return (self.makespan, self.total_distance)

    def payload(self) -> list[dict]:
        """Submission form: only vehicles that actually serve customers."""
        return [
            {"vehicle_id": i + 1, "stops": list(stops)}
            for i, stops in enumerate(self.routes)
            if len(stops) > 2
        ]

    def describe(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"makespan={self.makespan:.2f} distance={self.total_distance:.2f} "
            f"vehicles={len(self.used_routes())}"
        )


def cheapest_position(
    plan: Plan, route_index: int, customer: int
) -> tuple[int, PathStats] | None:
    """Cheapest feasible insertion position of ``customer`` inside one route.

    Returns ``(position, stats)`` with the position being the index in the *new* stop list, or
    ``None`` when no position keeps the route feasible.
    """
    stops = plan.routes[route_index]
    problem = plan.problem
    best: tuple[float, float, int, PathStats] | None = None
    for position in range(1, len(stops)):
        candidate = stops[:position] + [customer] + stops[position:]
        stats = problem.evaluate_path(candidate)
        if not stats.feasible:
            continue
        key = (stats.completion_min, stats.distance_km)
        if best is None or key < best[:2]:
            best = (key[0], key[1], position, stats)
    if best is None:
        return None
    return best[2], best[3]


def construct(problem: Problem, budget: Budget, order: Sequence[int] | None = None) -> Plan:
    """Sequential cheapest insertion, one customer at a time.

    Customers are visited in order of latest service start (earliest deadline first), which is a
    classic priority rule for time-window problems. Each customer goes to the position that
    minimises ``(new makespan, new total distance)``.

    Every candidate insertion costs one work unit. If the budget runs out the remaining
    customers are appended by nearest feasible position without accounting, so that a complete —
    if poorer — plan can still be submitted.
    """
    plan = Plan(problem)
    if order is None:
        order = sorted(
            problem.customer_ids,
            key=lambda cid: (problem.deadline(cid), problem.window(cid)[0], cid),
        )

    remaining: list[int] = []
    for offset, customer in enumerate(order):
        if budget.expired():
            remaining = list(order[offset:])
            break
        plan, placed = _insert_best(plan, customer, budget)
        if not placed:  # no feasible slot: take the least-bad one so nobody is forgotten
            plan, _ = _insert_best(plan, customer, None, allow_infeasible=True)

    for customer in remaining:  # budget exhausted: finish the plan without charging work
        plan, placed = _insert_best(plan, customer, None)
        if not placed:
            plan, _ = _insert_best(plan, customer, None, allow_infeasible=True)
    return plan


def _insert_best(
    plan: Plan,
    customer: int,
    budget: Budget | None,
    allow_infeasible: bool = False,
) -> tuple[Plan, bool]:
    """Insert one customer at the globally best position of the current plan.

    Returns ``(plan, placed)``; ``placed`` is ``False`` only when no position exists at all, which
    means the fleet has no room left even if rules are ignored.
    """
    problem = plan.problem
    best: tuple[float, float, int, list[int], PathStats] | None = None
    fallback: tuple[float, float, int, list[int], PathStats] | None = None

    for index, stops in enumerate(plan.routes):
        others = max(
            (s.completion_min for j, s in enumerate(plan.stats) if j != index), default=0.0
        )
        for position in range(1, len(stops)):
            candidate = stops[:position] + [customer] + stops[position:]
            if budget is not None:
                budget.spend()
            stats = problem.evaluate_path(candidate)
            makespan = max(others, stats.completion_min)
            distance = plan.total_distance - plan.stats[index].distance_km + stats.distance_km
            key = (makespan, distance)
            if stats.feasible:
                if best is None or key < best[:2]:
                    best = (makespan, distance, index, candidate, stats)
            elif allow_infeasible:
                penalty = (stats.lateness_min, makespan)
                if fallback is None or penalty < fallback[:2]:
                    fallback = (penalty[0], penalty[1], index, candidate, stats)

    chosen = best or fallback
    if chosen is None:
        # Not even an illegal slot exists: the fleet is too small for this customer set.
        return plan, False

    _, _, index, candidate, stats = chosen
    plan.set_route(index, candidate, stats)
    return plan, True


def relocate(plan: Plan, source: int, position: int, target: int, insert_at: int) -> Plan | None:
    """Return a copy of ``plan`` with one customer moved, or ``None`` if it breaks a rule."""
    if source == target and (insert_at == position or insert_at == position + 1):
        return None
    candidate = plan.copy()
    stops = list(candidate.routes[source])
    customer = stops.pop(position)
    new_source = candidate.problem.evaluate_path(stops)
    candidate.set_route(source, stops, new_source)
    if not new_source.feasible:
        return None

    target_stops = list(candidate.routes[target])
    if source == target and insert_at > position:
        insert_at -= 1
    insert_at = max(1, min(insert_at, len(target_stops) - 1))
    target_stops.insert(insert_at, customer)
    new_target = candidate.problem.evaluate_path(target_stops)
    if not new_target.feasible:
        return None
    candidate.set_route(target, target_stops, new_target)
    return candidate


def swap(plan: Plan, first: tuple[int, int], second: tuple[int, int]) -> Plan | None:
    """Swap two customers between positions ``(route, position)``; ``None`` if infeasible."""
    (ra, pa), (rb, pb) = first, second
    if ra == rb and pa == pb:
        return None
    candidate = plan.copy()

    if ra == rb:  # intra-route swap: one list, so no customer can be duplicated
        stops = list(candidate.routes[ra])
        stops[pa], stops[pb] = stops[pb], stops[pa]
        stats = candidate.problem.evaluate_path(stops)
        if not stats.feasible:
            return None
        candidate.set_route(ra, stops, stats)
        return candidate

    stops_a = list(candidate.routes[ra])
    stops_b = list(candidate.routes[rb])
    stops_a[pa], stops_b[pb] = stops_b[pb], stops_a[pa]
    stats_a = candidate.problem.evaluate_path(stops_a)
    stats_b = candidate.problem.evaluate_path(stops_b)
    if not (stats_a.feasible and stats_b.feasible):
        return None
    candidate.set_route(ra, stops_a, stats_a)
    candidate.set_route(rb, stops_b, stats_b)
    return candidate


def two_opt(plan: Plan, route_index: int, i: int, j: int) -> Plan | None:
    """Reverse ``stops[i:j + 1]`` inside one route, the classic intra-route move."""
    candidate = plan.copy()
    stops = list(candidate.routes[route_index])
    stops[i : j + 1] = reversed(stops[i : j + 1])
    stats = candidate.problem.evaluate_path(stops)
    if not stats.feasible:
        return None
    candidate.set_route(route_index, stops, stats)
    return candidate
