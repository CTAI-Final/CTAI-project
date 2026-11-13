"""Solver B — cheapest insertion followed by deterministic local search.

Search strategy
    The shared constructor builds a feasible plan; the improvement phase then runs
    best-improvement descent over three neighbourhoods until no move improves the lexicographic
    objective or the budget is exhausted:

    * **relocate** — move one customer to another position, in the same or in another route;
    * **swap** — exchange two customers between routes;
    * **2-opt** — reverse a segment inside one route (removes crossings).

    It is deterministic apart from the tie-breaking order, so five runs with five seeds give
    five identical results; the seeds are reported for completeness.

Documentation, pseudocode and complexity: ``docs/algorithms/local_search.md``.
"""

from __future__ import annotations

from typing import Iterator

from ..budget import Budget
from .base import Plan, construct, relocate, swap, two_opt

ALGORITHM_ID = "local_search"
ALGORITHM_NAME = "Cheapest insertion + relocate/swap/2-opt descent"
IS_DETERMINISTIC = True


def _relocate_moves(plan: Plan) -> Iterator[tuple[int, int, int, int]]:
    for source, stops in enumerate(plan.routes):
        for position in range(1, len(stops) - 1):
            for target, target_stops in enumerate(plan.routes):
                for insert_at in range(1, len(target_stops)):
                    yield source, position, target, insert_at


def _swap_moves(plan: Plan) -> Iterator[tuple[tuple[int, int], tuple[int, int]]]:
    positions = [
        (index, position)
        for index, stops in enumerate(plan.routes)
        for position in range(1, len(stops) - 1)
    ]
    for a in range(len(positions)):
        for b in range(a + 1, len(positions)):
            yield positions[a], positions[b]


def _two_opt_moves(plan: Plan) -> Iterator[tuple[int, int, int]]:
    for index, stops in enumerate(plan.routes):
        for i in range(1, len(stops) - 2):
            for j in range(i + 1, len(stops) - 1):
                yield index, i, j


def solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None:
    del seed  # the descent is deterministic
    budget: Budget = run_config["budget"]
    problem = submit_solution.problem

    plan = construct(problem, budget)
    if plan.feasible:
        submit_solution.submit(plan.payload())

    current = plan
    while not budget.expired():
        best = current
        best_key = current.objective()

        for source, position, target, insert_at in _relocate_moves(current):
            if budget.expired():
                return
            budget.spend()
            candidate = relocate(current, source, position, target, insert_at)
            if candidate is not None and candidate.objective() < best_key:
                best, best_key = candidate, candidate.objective()

        for first, second in _swap_moves(current):
            if budget.expired():
                return
            budget.spend()
            candidate = swap(current, first, second)
            if candidate is not None and candidate.objective() < best_key:
                best, best_key = candidate, candidate.objective()

        for index, i, j in _two_opt_moves(current):
            if budget.expired():
                return
            budget.spend()
            candidate = two_opt(current, index, i, j)
            if candidate is not None and candidate.objective() < best_key:
                best, best_key = candidate, candidate.objective()

        if best is current:
            return  # local optimum for the three neighbourhoods
        current = best
        submit_solution.submit(current.payload())
