"""Tabu search with relocate, swap and 2-opt. See docs/algorithms/tabu_search.md."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from itertools import combinations
from random import Random

from ..budget import Budget
from ..problem import PathStats, Problem
from ..submitter import SolutionSubmitter
from .base import Plan, relocate, swap, two_opt

ALGORITHM_ID = "tabu_search"
ALGORITHM_NAME = "Tabu search with relocate, swap and 2-opt"
IS_DETERMINISTIC = False

INITIAL_ATTEMPTS = 24
DEADLINE_JITTER_MIN = 25.0
TABU_TENURE = (5, 9)
RESTART_AFTER = 30
MAX_RESTARTS = 12

PlanKey = tuple[tuple[int, ...], ...]
Move = tuple[Callable[..., Plan | None], tuple]
Score = tuple[float, float]


def _construct(problem: Problem, budget: Budget, rng: Random | None) -> Plan | None:
    """Cheapest feasible insertion with a budget check for every trial."""
    order = sorted(
        problem.customer_ids,
        key=lambda customer: (
            problem.deadline(customer)
            + (rng.uniform(-DEADLINE_JITTER_MIN, DEADLINE_JITTER_MIN) if rng else 0.0),
            problem.window(customer)[0],
            customer,
        ),
    )
    plan = Plan(problem)
    for customer in order:
        best_key = (float("inf"), float("inf"))
        best: tuple[int, list[int], PathStats] | None = None
        for vehicle, stops in enumerate(plan.routes):
            other_completion = max(
                (stats.completion_min for i, stats in enumerate(plan.stats) if i != vehicle),
                default=0.0,
            )
            for position in range(1, len(stops)):
                if budget.expired():
                    return None
                budget.spend()
                trial = stops[:position] + [customer] + stops[position:]
                stats = problem.evaluate_path(trial)
                if not stats.feasible:
                    continue
                distance = sum(
                    (stats if i == vehicle else route_stats).distance_km
                    for i, route_stats in enumerate(plan.stats)
                )
                key = (max(other_completion, stats.completion_min), distance)
                if key < best_key:
                    best_key, best = key, (vehicle, trial, stats)
        if best is None:
            return None
        plan.set_route(*best)
    return plan


def _moves(plan: Plan) -> Iterator[Move]:
    positions = [
        (vehicle, position)
        for vehicle, stops in enumerate(plan.routes)
        for position in range(1, len(stops) - 1)
    ]
    for source, position in positions:
        for target, target_stops in enumerate(plan.routes):
            for insert_at in range(1, len(target_stops)):
                if source == target and insert_at in (position, position + 1):
                    continue
                yield relocate, (source, position, target, insert_at)

    for first, second in combinations(positions, 2):
        yield swap, (first, second)

    for vehicle, stops in enumerate(plan.routes):
        for i in range(1, len(stops) - 3):
            # A reversal of just two stops is already covered by swap.
            for j in range(i + 2, len(stops) - 1):
                yield two_opt, (vehicle, i, j)


def _plan_key(plan: Plan) -> PlanKey:
    return tuple(tuple(stops) for stops in plan.routes)


def _best_neighbor(
    current: Plan, best_score: Score, tabu: dict[PlanKey, int], budget: Budget
) -> tuple[Plan, Score] | None:
    chosen = None
    chosen_key = (float("inf"), float("inf"))
    for operator, args in _moves(current):
        if budget.expired():
            break
        budget.spend()
        neighbor = operator(current, *args)
        if neighbor is None:
            continue
        score = neighbor.objective()
        if score >= chosen_key:
            continue
        if score >= best_score and _plan_key(neighbor) in tabu:
            continue
        chosen_key = score
        chosen = (neighbor, score)
    return chosen


def solve(instance: dict, seed: int, run_config: dict, submit_solution: SolutionSubmitter) -> None:
    """Submit the first feasible plan and any subsequent fleet-wide improvements."""
    budget: Budget = run_config["budget"]
    problem = submit_solution.problem
    rng = Random(seed)

    for attempt in range(INITIAL_ATTEMPTS):
        if budget.expired():
            return
        current = _construct(problem, budget, rng if attempt else None)
        if current is not None:
            break
    else:
        return

    best_score = current.objective()
    submit_solution.submit(current.payload())
    tabu: dict[PlanKey, int] = {}
    step = 0
    stagnant_moves = 0
    restarts = 0

    while not budget.expired():
        step += 1
        tabu = {key: expires for key, expires in tabu.items() if expires >= step}
        chosen = _best_neighbor(current, best_score, tabu, budget)
        if chosen is None:
            if tabu:  # Advance the tabu clock if every feasible move is blocked.
                continue
            return

        # Different moves can lead back to the same plan.
        tabu[_plan_key(current)] = step + rng.randint(*TABU_TENURE)
        current, score = chosen
        if score < best_score:
            best_score = score
            submit_solution.submit(current.payload())
            stagnant_moves = 0
        else:
            stagnant_moves += 1

        if stagnant_moves >= RESTART_AFTER and restarts < MAX_RESTARTS and not budget.expired():
            restarts += 1
            stagnant_moves = 0
            restarted = _construct(problem, budget, rng)
            if restarted is not None:
                current = restarted
                tabu.clear()
                score = current.objective()
                if score < best_score:
                    best_score = score
                    submit_solution.submit(current.payload())
