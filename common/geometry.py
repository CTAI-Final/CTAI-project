"""Euclidean distance and travel time (rules Sections 2 and 4).

There are no roads, obstacles, or traffic congestion; any two locations are directly reachable.
Speed 0.5 km per minute -> travel time (minutes) = distance / 0.5.
"""

from __future__ import annotations

import math


def euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def travel_time(distance_km: float, speed_km_per_min: float = 0.5) -> float:
    """Travel time in minutes. Preprocessing cost of the distance matrix is recorded separately
    (rules Section 5)."""
    return distance_km / speed_km_per_min


def build_distance_matrix(inst: dict) -> list[list[float]]:
    """Node 0 is the depot, 1..n are the customers; returns the (n+1)x(n+1) symmetric distance
    matrix in kilometres."""
    pts = [(inst["depot"]["x"], inst["depot"]["y"])]
    pts += [(c["x"], c["y"]) for c in inst["customers"]]
    m = len(pts)
    mat = [[0.0] * m for _ in range(m)]
    for i in range(m):
        for j in range(i + 1, m):
            d = euclidean(*pts[i], *pts[j])
            mat[i][j] = mat[j][i] = d
    return mat
