"""欧氏距离与行驶时间（规则文档第二、四节）。

无道路、障碍物或交通拥堵；任意地点可直达。
速度 0.5 公里/分钟 → 行驶时间（分钟）= 距离 / 0.5。
"""

from __future__ import annotations

import math


def euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def travel_time(distance_km: float, speed_km_per_min: float = 0.5) -> float:
    """行驶时间（分钟）。预处理距离矩阵成本应单独记录（见规则第五节）。"""
    return distance_km / speed_km_per_min


def build_distance_matrix(inst: dict) -> list[list[float]]:
    """节点 0 为仓库，1..n 为客户；返回 (n+1)×(n+1) 对称距离矩阵（公里）。"""
    pts = [(inst["depot"]["x"], inst["depot"]["y"])]
    pts += [(c["x"], c["y"]) for c in inst["customers"]]
    m = len(pts)
    mat = [[0.0] * m for _ in range(m)]
    for i in range(m):
        for j in range(i + 1, m):
            d = euclidean(*pts[i], *pts[j])
            mat[i][j] = mat[j][i] = d
    return mat
