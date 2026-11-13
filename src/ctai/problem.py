"""Preprocessed scenario: distance matrix, customer lookup, fast path evaluation.

``Problem`` is the only place where the physical model (speed, service time, capacity, time
windows) is turned into numbers. Both the checker and every algorithm use it, so an algorithm
can never disagree with the checker about what a route costs or whether it is legal.

A *path* here is a full stop sequence that starts and ends at the depot, for example
``[0, 3, 7, 0]``. Route-level bookkeeping (vehicle ids, coverage) lives in :mod:`ctai.checker`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .geometry import build_distance_matrix

TOL = 1e-6


@dataclass(frozen=True)
class PathStats:
    """Result of driving one vehicle along a stop sequence."""

    feasible: bool
    completion_min: float
    distance_km: float
    load_kg: float
    service_start: tuple[float, ...]
    lateness_min: float

    @property
    def score(self) -> tuple[float, float]:
        """Lexicographic objective used for comparisons inside algorithms."""
        if not self.feasible:
            return (float("inf"), float("inf"))
        return (self.completion_min, self.distance_km)


class Problem:
    """Fast read-only view of one scenario."""

    def __init__(self, instance: dict, matrix: list[list[float]] | None = None) -> None:
        self.instance = instance
        self.matrix = matrix if matrix is not None else build_distance_matrix(instance)
        self.customers = {c["id"]: c for c in instance["customers"]}
        self.customer_ids: tuple[int, ...] = tuple(sorted(self.customers))
        self.vehicle_count: int = instance["vehicle_count"]
        self.capacity: float = instance["vehicle_capacity_kg"]
        self.speed: float = instance["speed_km_per_min"]
        self.service_time: float = instance["service_time_min"]
        self.scenario_id: str = instance["scenario_id"]
        self._demand = {cid: c["demand_kg"] for cid, c in self.customers.items()}
        self._window = {cid: tuple(c["time_window_min"]) for cid, c in self.customers.items()}

    # -- lookups ---------------------------------------------------------------------------
    def demand(self, customer_id: int) -> float:
        return self._demand[customer_id]

    def window(self, customer_id: int) -> tuple[float, float]:
        return self._window[customer_id]  # type: ignore[return-value]

    def deadline(self, customer_id: int) -> float:
        """Latest permitted service start; used for ordering heuristics."""
        return self._window[customer_id][1]  # type: ignore[index]

    def distance(self, a: int, b: int) -> float:
        return self.matrix[a][b]

    # -- evaluation ------------------------------------------------------------------------
    def evaluate_path(self, stops: Sequence[int]) -> PathStats:
        """Simulate one vehicle along ``stops``.

        The sequence is assumed to be ``[0, ...customers..., 0]``; structural mistakes such as a
        missing depot are reported by the checker, not here.
        """
        clock = 0.0
        distance = 0.0
        load = 0.0
        lateness = 0.0
        starts: list[float] = []
        feasible = True
        previous = stops[0] if stops else 0

        for stop in stops[1:]:
            leg = self.matrix[previous][stop]
            distance += leg
            arrival = clock + leg / self.speed

            if stop == 0:  # back at the depot; no further service
                clock = arrival
            else:
                load += self._demand[stop]
                earliest, latest = self._window[stop]
                start = arrival if arrival > earliest else earliest  # early arrival waits
                if start > latest + TOL:
                    feasible = False
                    lateness += start - latest
                starts.append(start)
                clock = start + self.service_time
            previous = stop

        if load > self.capacity + TOL:
            feasible = False

        return PathStats(
            feasible=feasible,
            completion_min=clock,
            distance_km=distance,
            load_kg=load,
            service_start=tuple(starts),
            lateness_min=lateness,
        )

    def empty_plan(self) -> list[list[int]]:
        """One empty route per vehicle: ``[[0, 0], [0, 0], ...]``."""
        return [[0, 0] for _ in range(self.vehicle_count)]

    def feasible_reference(self, plan: Sequence[Sequence[int]]) -> bool:
        """True when every route of ``plan`` is individually legal."""
        return all(self.evaluate_path(route).feasible for route in plan)
