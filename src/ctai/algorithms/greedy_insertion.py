"""Solver A — sequential cheapest insertion.

Search strategy
    Pure construction, no improvement phase. Customers are inserted one by one in earliest-deadline
    order, each at the position that minimises the resulting makespan and then the total distance.
    The result is a single pass: deterministic, fast, and easy to reason about, but it has no way
    to undo an early bad decision.

Documentation, pseudocode and complexity: ``docs/algorithms/greedy_insertion.md``.
"""

from __future__ import annotations

from .base import construct

ALGORITHM_ID = "greedy_insertion"
ALGORITHM_NAME = "Sequential cheapest insertion (construction only)"
IS_DETERMINISTIC = True


def solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None:
    """Build one plan and submit it.

    The algorithm is deterministic, so ``seed`` does not change the result; it is accepted
    because the harness always passes it.
    """
    del seed  # deterministic construction
    budget = run_config["budget"]
    problem = submit_solution.problem

    plan = construct(problem, budget)
    submit_solution.submit(plan.payload())
