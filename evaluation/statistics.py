"""分组统计（规则文档第八节）。

- 标准差使用样本标准差（分母 m−1，m 为合法运行次数；待审核）；
- 失败不记成 0 分钟；全部失败时质量指标为 None（JSON null，不用 NaN/Infinity）；
- 不混合两种停止规则的耗时；
- 质量对比优先使用各算法都至少成功一次的共同场景，等权汇总。
"""

from __future__ import annotations

import math
from collections import defaultdict


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _sample_std(xs: list[float]) -> float | None:
    """样本标准差；合法次数不足 2 次时返回 None（不足以评价波动）。"""
    if len(xs) < 2:
        return None
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def summarize_scenario(records: list[dict]) -> dict:
    """单场景 5 次运行记录 → 指标汇总。

    records: 每项至少含 feasible / makespan_min / total_distance_km /
             solver_runtime_sec / termination / work_completed。
    """
    feasible = [r for r in records if r.get("feasible")]
    makespans = [r["makespan_min"] for r in feasible if r["makespan_min"] is not None]
    dists = [r["total_distance_km"] for r in feasible if r["total_distance_km"] is not None]
    runtimes = [r["solver_runtime_sec"] for r in records
                if r.get("solver_runtime_sec") is not None]
    return {
        "runs": len(records),
        "feasible_runs": len(feasible),
        "success_rate": len(feasible) / len(records) if records else None,
        "makespan_mean": _mean(makespans),
        "makespan_std": _sample_std(makespans),
        "distance_mean": _mean(dists),
        "runtime_mean": _mean(runtimes),
        "best_run": min(feasible, key=lambda r: (r["makespan_min"],
                                                 r["total_distance_km"]),
                        default=None),
    }


def common_scenarios(per_algorithm: dict[str, set[str]]) -> set[str]:
    """所有算法都至少成功一次的场景集合。"""
    sets = list(per_algorithm.values())
    return set.intersection(*sets) if sets else set()


def group_summaries(results: list[dict], group_key: str) -> dict:
    """按组（如 简单/中等/困难 或 10/20/40 客户）汇总；等权平均。"""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        grouped[r.get(group_key, "unknown")].append(r)
    return {g: summarize_scenario(rs) for g, rs in grouped.items()}
