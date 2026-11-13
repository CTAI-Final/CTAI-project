"""Solver C — cheapest insertion followed by simulated annealing.

Search strategy
    The constructor gives a feasible start; the search then accepts random neighbours drawn from
    the same three neighbourhoods as Solver B, but also accepts worse moves with probability
    ``exp(-delta / T)``. That lets the search leave a poor local optimum, which is exactly the
    weakness of the deterministic descent.

    Temperature starts at 2 % of the initial makespan, cools geometrically per evaluated move and
    is reheated when it drops below 10 % of its starting value, so a long fixed-work run keeps
    exploring instead of freezing early.

Documentation, pseudocode and complexity: ``docs/algorithms/simulated_annealing.md``.
"""

from __future__ import annotations

import math
import random

from ..budget import Budget
from .base import Plan, construct, relocate, swap, two_opt

ALGORITHM_ID = "simulated_annealing"
ALGORITHM_NAME = "Cheapest insertion + simulated annealing"
IS_DETERMINISTIC = False

DISTANCE_WEIGHT = 0.02  # 1 km ~ 0.02 min, keeps distance as a light tie-breaker
COOLING = 0.9993
REHEAT_FRACTION = 0.1


def _scalar(plan: Plan) -> float:
    """Single scalar energy; the lexicographic objective is kept for the final comparison."""
    if not plan.feasible:
        return float("inf")
    return plan.makespan + DISTANCE_WEIGHT * plan.total_distance


def _random_neighbour(plan: Plan, rng: random.Random) -> Plan | None:
    routes = plan.routes
    non_empty = [i for i, stops in enumerate(routes) if len(stops) > 2]
    if not non_empty:
        return None

    roll = rng.random()
    if roll < 0.55:  # relocate
        source = rng.choice(non_empty)
        position = rng.randrange(1, len(routes[source]) - 1)
        target = rng.randrange(len(routes))
        insert_at = rng.randrange(1, len(routes[target]))
        return relocate(plan, source, position, target, insert_at)
    if roll < 0.85:  # swap
        first = rng.choice(non_empty)
        second = rng.choice(non_empty)
        return swap(
            plan,
            (first, rng.randrange(1, len(routes[first]) - 1)),
            (second, rng.randrange(1, len(routes[second]) - 1)),
        )
    index = rng.choice(non_empty)  # 2-opt
    stops = routes[index]
    if len(stops) < 5:
        return None
    i = rng.randrange(1, len(stops) - 2)
    j = rng.randrange(i + 1, len(stops) - 1)
    return two_opt(plan, index, i, j)


def solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None:
    budget: Budget = run_config["budget"]
    problem = submit_solution.problem
    rng = random.Random(seed)

    plan = construct(problem, budget)
    if plan.feasible:
        submit_solution.submit(plan.payload())

    current = plan
    best = plan
    best_key = plan.objective()

    start_temperature = max(0.5, 0.02 * max(plan.makespan, 1.0))
    temperature = start_temperature
    floor = start_temperature * REHEAT_FRACTION
    energy = _scalar(current)

    while not budget.expired():
        budget.spend()
        candidate = _random_neighbour(current, rng)
        if candidate is None:
            continue

        candidate_energy = _scalar(candidate)
        delta = candidate_energy - energy
        if delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 1e-9)):
            current = candidate
            energy = candidate_energy
            key = candidate.objective()
            if key < best_key:
                best, best_key = candidate, key
                submit_solution.submit(best.payload())

        temperature *= COOLING
        if temperature < floor:
            temperature = start_temperature * 0.5  # partial reheat, keeps the run exploring
