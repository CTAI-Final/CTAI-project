"""场景 JSON 读取与输入校验（规则文档第二、十一节）。"""

from __future__ import annotations

import json
from pathlib import Path

TOL = 1e-6  # 数值比较容差（对应各自单位，待审核冻结）


def load_instance(path: str | Path) -> dict:
    """读取场景 JSON 并做基础校验，返回字典。"""
    with open(path, encoding="utf-8") as f:
        inst = json.load(f)
    errors = validate_instance(inst)
    if errors:
        raise ValueError(f"场景 {inst.get('scenario_id', '?')} 输入非法: {errors}")
    return inst


def validate_instance(inst: dict) -> list[str]:
    """校验输入字段；返回错误信息列表，空列表表示合法。"""
    errors: list[str] = []
    required = [
        "schema_version", "scenario_id", "depot", "customer_count",
        "vehicle_count", "vehicle_capacity_kg", "speed_km_per_min",
        "service_time_min", "customers",
    ]
    for key in required:
        if key not in inst:
            errors.append(f"缺少字段: {key}")

    depot = inst.get("depot", {})
    if depot.get("id", None) != 0:
        errors.append("仓库编号必须为 0")

    customers = inst.get("customers", [])
    n = inst.get("customer_count", len(customers))
    if n != len(customers):
        errors.append(f"customer_count({n}) 与 customers 数组长度({len(customers)})不一致")

    ids = [c.get("id") for c in customers]
    expected = list(range(1, len(customers) + 1))
    if sorted(ids) != expected:
        errors.append(f"客户编号应为 1..{len(customers)}，实际为 {ids}")

    for c in customers:
        w = c.get("demand_kg", 0)
        if not (0 < w <= inst.get("vehicle_capacity_kg", 100) + TOL):
            errors.append(f"客户 {c.get('id')} 需求非法: {w}")
        a, b = c.get("time_window_min", [None, None])
        if a is None or b is None or not (0 <= a <= b):
            errors.append(f"客户 {c.get('id')} 时间窗非法: {c.get('time_window_min')}")
        x, y = c.get("x"), c.get("y")
        if not (0 <= x <= 20 and 0 <= y <= 20):
            errors.append(f"客户 {c.get('id')} 坐标超出 [0,20]: ({x}, {y})")

    d = depot
    if not (0 <= d.get("x", -1) <= 20 and 0 <= d.get("y", -1) <= 20):
        errors.append(f"仓库坐标超出 [0,20]: ({d.get('x')}, {d.get('y')})")

    if inst.get("vehicle_count", 0) < 1:
        errors.append("vehicle_count 至少为 1")
    return errors
