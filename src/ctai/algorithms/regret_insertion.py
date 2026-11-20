"""Regret-k construction using one best insertion per vehicle."""
from __future__ import annotations

from dataclasses import dataclass

from ctai.budget import Budget
from ctai.problem import PathStats, Problem

ALGORITHM_ID = "regret_insertion"
ALGORITHM_NAME = "Regret-k insertion (default k=2)"
IS_DETERMINISTIC = True


@dataclass
class Option:
    score: tuple[float, float]
    vehicle: int
    position: int
    stops: list[int]
    stats: PathStats


def priority(options: list[Option], k: int, deadline: float, customer: int) -> tuple:
    """Maximize scarcity, then summed lexicographic regret; deterministic ties."""
    best = options[0].score
    count = min(k, len(options))
    regret = tuple(sum(o.score[j] - best[j] for o in options[1:count]) for j in (0, 1))
    return (max(0, k - len(options)), *regret, -best[0], -best[1], -deadline, -customer)


def solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None:
    """Submit only a complete feasible construction; stop before exceeding work budget."""
    del instance, seed
    k = run_config.get("regret_k", 2)
    if isinstance(k, bool) or not isinstance(k, int) or k < 2:
        raise ValueError("regret_k must be an integer >= 2")
    problem: Problem = submit_solution.problem
    budget: Budget = run_config["budget"]
    routes = problem.empty_plan()
    # Empty-route summaries need no candidate simulation.
    stats = [PathStats(True, 0.0, 0.0, 0.0, (), 0.0) for _ in routes]
    pending = set(problem.customer_ids)
    effective_k = min(k, len(routes))
    while pending:
        selected = None
        total_distance = sum(s.distance_km for s in stats)
        for customer in sorted(pending):
            options = []
            for vehicle, stops in enumerate(routes):
                other_max = max((s.completion_min for j, s in enumerate(stats)
                                 if j != vehicle), default=0.0)
                best = None
                for position in range(1, len(stops)):
                    if budget.expired():
                        return
                    candidate = stops[:position] + [customer] + stops[position:]
                    budget.spend()
                    result = problem.evaluate_path(candidate)
                    if not result.feasible:
                        continue
                    score = (max(other_max, result.completion_min),
                             total_distance - stats[vehicle].distance_km + result.distance_km)
                    option = Option(score, vehicle, position, candidate, result)
                    if best is None or (score, position) < (best.score, best.position):
                        best = option
                if best is not None:
                    options.append(best)
            # Insertion alone cannot repair a customer with no feasible placement.
            if not options:
                return
            options.sort(key=lambda o: (o.score, o.vehicle, o.position))
            key = priority(options, effective_k, problem.deadline(customer), customer)
            if selected is None or key > selected[0]:
                selected = (key, customer, options[0])
        _, customer, option = selected
        routes[option.vehicle] = option.stops
        stats[option.vehicle] = option.stats
        pending.remove(customer)
    submit_solution.submit([
        {"vehicle_id": i + 1, "stops": route}
        for i, route in enumerate(routes) if len(route) > 2
    ])
