"""CTAI 公共模块：场景读取、几何计算、合法性检查、结果提交。

本目录由出题方维护；算法实现者只调用，不修改。
"""

from .instance import load_instance, validate_instance
from .geometry import euclidean, travel_time, build_distance_matrix
from .checker import evaluate_routes

__all__ = [
    "load_instance", "validate_instance",
    "euclidean", "travel_time", "build_distance_matrix",
    "evaluate_routes",
]
