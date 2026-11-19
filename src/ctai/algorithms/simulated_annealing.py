"""Solver C — penalty-guided simulated annealing with critical-route moves and restarts.

Search strategy
    1. Build a start plan with the shared cheapest-insertion constructor.
    2. Calibrate the initial temperature from a sample of real uphill moves, so that roughly
       ``INITIAL_ACCEPTANCE`` of worsening moves are accepted at the start, whatever the scale
       of the scenario.
    3. Anneal: draw one random neighbour from five neighbourhoods (relocate, swap, 2-opt,
       or-opt, 2-opt*), biased towards the route that defines the makespan. Better moves are
       always accepted; worse moves with probability ``exp(-delta / T)``.
    4. Infeasible plans are allowed *inside* the search with a penalty on lateness and overload
       whose weight adapts to how often the current plan is infeasible. Only feasible plans are
       ever submitted, so the harness never sees a broken plan.
    5. The temperature cools geometrically over one epoch. At the end of an epoch, or after a
       long stall, the search restarts from the best plan found so far with a reheated (lower)
       temperature.

Documentation, pseudocode and complexity: ``docs/algorithms/simulated_annealing.md``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..budget import Budget
from ..problem import PathStats, Problem
from .base import construct

ALGORITHM_ID = "simulated_annealing"
ALGORITHM_NAME = "Penalty-guided simulated annealing with restarts"
IS_DETERMINISTIC = False


# -- parameters ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class Parameters:
    """All tunable settings in one place; frozen before the formal runs."""

    # energy
    distance_weight: float = 0.05  # minutes of energy per km; tie-breaker on distance
    spread_weight: float = 0.02  # weight on the mean route completion; breaks the max plateau
    penalty_initial: float = 3.0  # energy per minute late / per kg overloaded
    penalty_min: float = 0.5
    penalty_max: float = 1000.0
    penalty_factor: float = 1.2  # multiplicative update of the penalty weight
    penalty_period: int = 100  # moves between two penalty updates

    # temperature schedule
    calibration_moves: int = 200  # sampled moves used to choose T0 (counted as work)
    initial_acceptance: float = 0.1  # target probability of accepting an average uphill move
    epoch_moves: int = 10_000  # moves per cooling cycle
    final_ratio: float = 0.002  # T at the end of an epoch = final_ratio * T0
    reheat_decay: float = 0.6  # each restart begins at reheat_decay * previous start T
    reheat_floor: float = 0.1  # but never below reheat_floor * T0
    stall_moves: int = 10_000  # restart early if the best has not improved for this long

    # neighbourhood mix (cumulative thresholds are derived below)
    p_relocate: float = 0.35
    p_swap: float = 0.20
    p_two_opt: float = 0.15
    p_or_opt: float = 0.15
    p_two_opt_star: float = 0.15
    p_critical: float = 0.5  # probability that the first customer is taken from the makespan route


DEFAULT_PARAMETERS = Parameters()


# -- search state --------------------------------------------------------------------------------
class _State:
    """Routes plus cached per-route statistics and penalty terms.

    ``routes[i]`` is the stop list of vehicle ``i + 1`` and always starts and ends with depot
    ``0``. Unused vehicles are kept as ``[0, 0]`` so that a move can open a new route.
    """

    __slots__ = ("problem", "routes", "stats", "violation")

    def __init__(self, problem: Problem, routes: list[list[int]]) -> None:
        self.problem = problem
        self.routes = [list(r) for r in routes]
        self.stats = [problem.evaluate_path(r) for r in self.routes]
        self.violation = [_violation(problem, s) for s in self.stats]

    def copy(self) -> _State:
        clone = _State.__new__(_State)
        clone.problem = self.problem
        clone.routes = [list(r) for r in self.routes]
        clone.stats = list(self.stats)
        clone.violation = list(self.violation)
        return clone

    def apply(self, changes: dict[int, tuple[list[int], PathStats, float]]) -> None:
        for index, (stops, stats, violation) in changes.items():
            self.routes[index] = stops
            self.stats[index] = stats
            self.violation[index] = violation

    @property
    def feasible(self) -> bool:
        return all(s.feasible for s in self.stats)  # same tolerance as the checker

    def objective(self) -> tuple[float, float]:
        """The harness ranking: makespan first, total distance second."""
        if not self.feasible:
            return (math.inf, math.inf)
        makespan = max((s.completion_min for s in self.stats), default=0.0)
        return (makespan, sum(s.distance_km for s in self.stats))

    def payload(self) -> list[dict]:
        return [
            {"vehicle_id": i + 1, "stops": list(stops)}
            for i, stops in enumerate(self.routes)
            if len(stops) > 2
        ]

    def critical_route(self) -> int:
        return max(range(len(self.stats)), key=lambda i: self.stats[i].completion_min)


def _violation(problem: Problem, stats: PathStats) -> float:
    """Total constraint violation of one route: minutes late plus kilograms overloaded."""
    overload = max(0.0, stats.load_kg - problem.capacity)
    return stats.lateness_min + overload


def _energy(
    stats: list[PathStats], violation: list[float], penalty: float, params: Parameters
) -> float:
    """Scalar energy minimised by the annealer.

    ``makespan`` is the real objective. Because it is a maximum, most moves on non-critical
    routes leave it unchanged; the small ``spread`` term (mean route completion) and the
    distance term give those moves a slope without overriding the makespan.
    """
    completions = [s.completion_min for s in stats]
    makespan = max(completions, default=0.0)
    spread = sum(completions) / len(completions) if completions else 0.0
    distance = sum(s.distance_km for s in stats)
    return (
        makespan
        + params.spread_weight * spread
        + params.distance_weight * distance
        + penalty * sum(violation)
    )


# -- neighbourhoods ------------------------------------------------------------------------------
Changes = dict[int, list[int]]  # route index -> new stop list


def _pick_customer(state: _State, rng: random.Random, params: Parameters) -> tuple[int, int]:
    """Choose ``(route, position)`` of one customer, biased towards the makespan route."""
    used = [i for i, r in enumerate(state.routes) if len(r) > 2]
    critical = state.critical_route()
    if len(state.routes[critical]) > 2 and rng.random() < params.p_critical:
        route = critical
    else:
        route = rng.choice(used)
    return route, rng.randrange(1, len(state.routes[route]) - 1)


def _relocate(state: _State, rng: random.Random, params: Parameters) -> Changes | None:
    """Move one customer to a random position in any route (an empty route opens a vehicle)."""
    source, position = _pick_customer(state, rng, params)
    target = rng.randrange(len(state.routes))
    source_stops = list(state.routes[source])
    customer = source_stops.pop(position)
    if target == source:
        insert_at = rng.randrange(1, len(source_stops))
        if insert_at == position:
            return None  # would recreate the same route
        source_stops.insert(insert_at, customer)
        return {source: source_stops}
    target_stops = list(state.routes[target])
    target_stops.insert(rng.randrange(1, len(target_stops)), customer)
    return {source: source_stops, target: target_stops}


def _swap(state: _State, rng: random.Random, params: Parameters) -> Changes | None:
    """Exchange two customers, in the same route or in two different routes."""
    ra, pa = _pick_customer(state, rng, params)
    used = [i for i, r in enumerate(state.routes) if len(r) > 2]
    rb = rng.choice(used)
    pb = rng.randrange(1, len(state.routes[rb]) - 1)
    if ra == rb:
        if pa == pb:
            return None
        stops = list(state.routes[ra])
        stops[pa], stops[pb] = stops[pb], stops[pa]
        return {ra: stops}
    stops_a = list(state.routes[ra])
    stops_b = list(state.routes[rb])
    stops_a[pa], stops_b[pb] = stops_b[pb], stops_a[pa]
    return {ra: stops_a, rb: stops_b}


def _two_opt(state: _State, rng: random.Random, params: Parameters) -> Changes | None:
    """Reverse a segment inside one route (removes crossings, reorders around time windows)."""
    route, i = _pick_customer(state, rng, params)
    stops = state.routes[route]
    if len(stops) < 4:
        return None  # fewer than two customers: nothing to reverse
    j = rng.randrange(1, len(stops) - 1)
    if i == j:
        return None
    i, j = min(i, j), max(i, j)
    new = stops[:i] + stops[i : j + 1][::-1] + stops[j + 1 :]
    return {route: new}


def _or_opt(state: _State, rng: random.Random, params: Parameters) -> Changes | None:
    """Move a chain of two or three consecutive customers to another place, keeping its order."""
    source, start = _pick_customer(state, rng, params)
    stops = state.routes[source]
    length = rng.choice((2, 3))
    if start + length > len(stops) - 1:
        return None  # chain would run into the closing depot
    segment = stops[start : start + length]
    remaining = stops[:start] + stops[start + length :]
    target = rng.randrange(len(state.routes))
    if target == source:
        insert_at = rng.randrange(1, len(remaining))
        if insert_at == start:
            return None
        return {source: remaining[:insert_at] + segment + remaining[insert_at:]}
    target_stops = state.routes[target]
    insert_at = rng.randrange(1, len(target_stops))
    return {
        source: remaining,
        target: target_stops[:insert_at] + segment + target_stops[insert_at:],
    }


def _two_opt_star(state: _State, rng: random.Random, params: Parameters) -> Changes | None:
    """Exchange the tails of two routes; with an empty route this splits a long route in two."""
    first, cut_a = _pick_customer(state, rng, params)
    second = rng.randrange(len(state.routes))
    if second == first:
        return None
    a = state.routes[first]
    b = state.routes[second]
    cut_b = rng.randrange(1, len(b))  # tail of b starts at cut_b (may be just the depot)
    new_a = a[:cut_a] + b[cut_b:]
    new_b = b[:cut_b] + a[cut_a:]
    if new_a == a:
        return None
    return {first: new_a, second: new_b}


def _move_table(params: Parameters):
    moves = (
        (params.p_relocate, _relocate),
        (params.p_swap, _swap),
        (params.p_two_opt, _two_opt),
        (params.p_or_opt, _or_opt),
        (params.p_two_opt_star, _two_opt_star),
    )
    total = sum(weight for weight, _ in moves)
    table, running = [], 0.0
    for weight, move in moves:
        running += weight / total
        table.append((running, move))
    return table


def _random_neighbour(state: _State, rng: random.Random, params: Parameters, table) -> Changes | None:
    if all(len(r) <= 2 for r in state.routes):
        return None
    roll = rng.random()
    for threshold, move in table:
        if roll < threshold:
            return move(state, rng, params)
    return table[-1][1](state, rng, params)


# -- annealing -----------------------------------------------------------------------------------
class _Annealer:
    """One annealing run over a fixed problem; separated from ``solve`` for readability."""

    def __init__(
        self,
        problem: Problem,
        budget: Budget,
        rng: random.Random,
        submit_solution,
        params: Parameters = DEFAULT_PARAMETERS,
    ) -> None:
        self.problem = problem
        self.budget = budget
        self.rng = rng
        self.submit_solution = submit_solution
        self.params = params
        self.table = _move_table(params)
        self.penalty = params.penalty_initial
        self.best: _State | None = None
        self.best_key: tuple[float, float] = (math.inf, math.inf)
        self.current: _State | None = None
        self.energy = math.inf

    # -- helpers ---------------------------------------------------------------------------
    def _evaluate(self, changes: Changes) -> tuple[dict, float]:
        """Evaluate only the touched routes; returns the cached update and the new energy."""
        current = self.current
        assert current is not None
        updates: dict[int, tuple[list[int], PathStats, float]] = {}
        for index, stops in changes.items():
            stats = self.problem.evaluate_path(stops)
            updates[index] = (stops, stats, _violation(self.problem, stats))
        stats = list(current.stats)
        violation = list(current.violation)
        for index, (_, s, v) in updates.items():
            stats[index] = s
            violation[index] = v
        return updates, _energy(stats, violation, self.penalty, self.params)

    def _recompute_energy(self) -> None:
        assert self.current is not None
        self.energy = _energy(
            self.current.stats, self.current.violation, self.penalty, self.params
        )

    def _record_if_best(self) -> bool:
        """Submit ``current`` if it is feasible and lexicographically better than the best."""
        current = self.current
        assert current is not None
        key = current.objective()
        if key < self.best_key:
            self.best = current.copy()
            self.best_key = key
            self.submit_solution.submit(self.best.payload())
            return True
        return False

    def _update_penalty(self) -> None:
        """Raise the penalty while the search sits in infeasible space, relax it otherwise."""
        assert self.current is not None
        p = self.params
        if self.current.feasible:
            self.penalty = max(p.penalty_min, self.penalty / p.penalty_factor)
        else:
            self.penalty = min(p.penalty_max, self.penalty * p.penalty_factor)
        self._recompute_energy()

    def _calibrate_temperature(self) -> float:
        """Pick T0 so that an average uphill move is accepted with ``initial_acceptance``."""
        uphill: list[float] = []
        for _ in range(self.params.calibration_moves):
            if self.budget.expired():
                break
            self.budget.spend()
            changes = _random_neighbour(self.current, self.rng, self.params, self.table)
            if changes is None:
                continue
            _, energy = self._evaluate(changes)
            if energy > self.energy:
                uphill.append(energy - self.energy)
        if not uphill:
            return 1.0
        mean = sum(uphill) / len(uphill)
        return max(1e-3, -mean / math.log(self.params.initial_acceptance))

    # -- main loop -------------------------------------------------------------------------
    def run(self, start_routes: list[list[int]]) -> None:
        p = self.params
        self.current = _State(self.problem, start_routes)
        self._recompute_energy()
        self._record_if_best()

        t0 = self._calibrate_temperature()
        epoch_start_t = t0
        temperature = t0
        cooling = p.final_ratio ** (1.0 / p.epoch_moves)
        moves_in_epoch = 0
        since_best = 0
        step = 0

        while not self.budget.expired():
            self.budget.spend()  # one work unit = one proposed neighbour
            step += 1
            moves_in_epoch += 1
            since_best += 1

            changes = _random_neighbour(self.current, self.rng, p, self.table)
            if changes is not None:
                updates, energy = self._evaluate(changes)
                delta = energy - self.energy
                if delta <= 0.0 or self.rng.random() < math.exp(-delta / temperature):
                    self.current.apply(updates)
                    self.energy = energy
                    if self._record_if_best():
                        since_best = 0

            if step % p.penalty_period == 0:
                self._update_penalty()

            temperature *= cooling
            if moves_in_epoch >= p.epoch_moves or since_best >= p.stall_moves:
                # Restart from the incumbent with a smaller reheat: intensify around the best.
                if self.best is not None:
                    self.current = self.best.copy()
                    self._recompute_energy()
                epoch_start_t = max(p.reheat_floor * t0, p.reheat_decay * epoch_start_t)
                temperature = epoch_start_t
                moves_in_epoch = 0
                since_best = 0


def solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None:
    """Harness entry point; see ``docs/interface.md``."""
    del instance  # the preprocessed ``submit_solution.problem`` is used instead
    budget: Budget = run_config["budget"]
    problem = submit_solution.problem
    rng = random.Random(seed)

    start = construct(problem, budget)  # may be infeasible on hard data; the penalty repairs it
    _Annealer(problem, budget, rng, submit_solution).run(start.routes)
