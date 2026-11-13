"""Euclidean geometry and travel time.

The problem is defined on a plain 20 km x 20 km square with no roads, obstacles or congestion:
any two locations are directly reachable and the travel distance is the Euclidean distance.
Vehicle speed is fixed, so travel time in minutes is ``distance / speed``.

See ``docs/rules.md`` Sections 2 and 4.
"""

from __future__ import annotations

import math
from typing import Sequence

Point = tuple[float, float]


def euclidean(p: Point, q: Point) -> float:
    """Euclidean distance in kilometres between two points."""
    return math.hypot(q[0] - p[0], q[1] - p[1])


def travel_minutes(distance_km: float, speed_km_per_min: float = 0.5) -> float:
    """Convert a distance in kilometres to travel time in minutes."""
    return distance_km / speed_km_per_min


def build_distance_matrix(instance: dict) -> list[list[float]]:
    """Return the symmetric ``(n + 1) x (n + 1)`` distance matrix in kilometres.

    Index 0 is the depot, indices 1..n are the customers in the order they appear in the
    scenario file, which is also their ``id`` order (the loader enforces this).
    """
    points: list[Point] = [(instance["depot"]["x"], instance["depot"]["y"])]
    points += [(c["x"], c["y"]) for c in instance["customers"]]

    size = len(points)
    matrix = [[0.0] * size for _ in range(size)]
    for i in range(size):
        xi, yi = points[i]
        for j in range(i + 1, size):
            xj, yj = points[j]
            d = math.hypot(xj - xi, yj - yi)
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def route_points(instance: dict, stops: Sequence[int]) -> list[Point]:
    """Coordinates of a stop sequence, for plotting and debugging."""
    lookup: dict[int, Point] = {0: (instance["depot"]["x"], instance["depot"]["y"])}
    lookup.update({c["id"]: (c["x"], c["y"]) for c in instance["customers"]})
    return [lookup[s] for s in stops]
