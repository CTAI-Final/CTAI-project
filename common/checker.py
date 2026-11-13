"""合法性检查器与指标计算（规则文档第三、四、八节）。

检查项：起终点、客户覆盖、重复服务、车辆数、容量、时间窗、回仓。
评价口径：内部使用完整浮点精度，比较容差 TOL；不得逐路段四舍五入后再累计。
"""

from __future__ import annotations

from .geometry import build_distance_matrix

TOL = 1e-6


def evaluate_routes(inst: dict, routes: list[dict]) -> dict:
    """评估一组路线。

    routes: [{"vehicle_id": int, "stops": [0, c..., 0]}, ...]
    返回 {"feasible", "makespan_min", "total_distance_km", "validation_errors"}。
    """
    errors: list[str] = []
    n = inst["customer_count"]
    cap = inst["vehicle_capacity_kg"]
    speed = inst["speed_km_per_min"]
    t_service = inst["service_time_min"]
    mat = build_distance_matrix(inst)

    cust = {c["id"]: c for c in inst["customers"]}
    used_ids = [r.get("vehicle_id") for r in routes]

    # 车辆编号
    if len(set(used_ids)) != len(used_ids):
        errors.append("vehicle_id 重复")
    if used_ids and (min(used_ids) < 1 or max(used_ids) > inst["vehicle_count"]):
        errors.append(f"vehicle_id 超出 1..{inst['vehicle_count']}")

    # 覆盖与重复
    served: list[int] = []
    for r in routes:
        stops = r.get("stops", [])
        served += [s for s in stops[1:-1]]
    if sorted(served) != list(range(1, n + 1)):
        missing = sorted(set(range(1, n + 1)) - set(served))
        dup = sorted({s for s in served if served.count(s) > 1})
        if missing:
            errors.append(f"漏送客户: {missing}")
        if dup:
            errors.append(f"重复服务客户: {dup}")

    makespan = 0.0
    total_dist = 0.0

    for r in routes:
        stops = r.get("stops", [])
        if len(stops) < 2 or stops[0] != 0 or stops[-1] != 0:
            errors.append(f"车辆 {r.get('vehicle_id')} 路线必须以仓库 0 开始并结束")
            continue

        load = sum(cust[s]["demand_kg"] for s in stops[1:-1])
        if load > cap + TOL:
            errors.append(f"车辆 {r.get('vehicle_id')} 超载: {load} > {cap} kg")

        t = 0.0          # 从时间 0 的仓库出发
        last = 0
        for s in stops[1:]:
            d = mat[last][s]
            total_dist += d
            arrive = t + d / speed
            if s == 0:
                t = arrive          # 回仓，不再出发
            else:
                a, b = cust[s]["time_window_min"]
                start = max(arrive, a)          # 提前到达须等待至 a
                if start > b + TOL:             # 开始服务不得晚于 b
                    errors.append(
                        f"客户 {s} 时间窗违规: 开始服务 {start:.6f} > {b}")
                t = start + t_service
                last = s
                continue
            last = s

        makespan = max(makespan, t)

    feasible = not errors
    return {
        "feasible": feasible,
        "makespan_min": makespan if feasible else None,
        "total_distance_km": total_dist if feasible else None,
        "validation_errors": errors,
    }
