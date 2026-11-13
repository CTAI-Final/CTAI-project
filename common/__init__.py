"""CTAI common package: scenario loading, geometry, legality checking, result submission.

This directory is maintained by the project owner. Algorithm implementers import it but
must not modify it.
"""

from .instance import load_instance, validate_instance
from .geometry import euclidean, travel_time, build_distance_matrix
from .checker import evaluate_routes

__all__ = [
    "load_instance", "validate_instance",
    "euclidean", "travel_time", "build_distance_matrix",
    "evaluate_routes",
]
