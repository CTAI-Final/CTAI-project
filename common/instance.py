"""Scenario JSON loading and input validation (rules Sections 2 and 11)."""

from __future__ import annotations

import json
from pathlib import Path

TOL = 1e-6  # numerical comparison tolerance (in the respective unit; pending freeze)


def load_instance(path: str | Path) -> dict:
    """Load a scenario JSON file, validate it, and return it as a dict."""
    with open(path, encoding="utf-8") as f:
        inst = json.load(f)
    errors = validate_instance(inst)
    if errors:
        raise ValueError(
            f"Scenario {inst.get('scenario_id', '?')} has an invalid input: {errors}")
    return inst


def validate_instance(inst: dict) -> list[str]:
    """Validate the input fields; return a list of errors (empty means valid)."""
    errors: list[str] = []
    required = [
        "schema_version", "scenario_id", "depot", "customer_count",
        "vehicle_count", "vehicle_capacity_kg", "speed_km_per_min",
        "service_time_min", "customers",
    ]
    for key in required:
        if key not in inst:
            errors.append(f"missing field: {key}")

    depot = inst.get("depot", {})
    if depot.get("id", None) != 0:
        errors.append("depot id must be 0")

    customers = inst.get("customers", [])
    n = inst.get("customer_count", len(customers))
    if n != len(customers):
        errors.append(
            f"customer_count({n}) does not match the length of the customers array "
            f"({len(customers)})")

    ids = [c.get("id") for c in customers]
    expected = list(range(1, len(customers) + 1))
    if sorted(ids) != expected:
        errors.append(f"customer ids must be 1..{len(customers)}, got {ids}")

    for c in customers:
        w = c.get("demand_kg", 0)
        if not (0 < w <= inst.get("vehicle_capacity_kg", 100) + TOL):
            errors.append(f"customer {c.get('id')} has an invalid demand: {w}")
        a, b = c.get("time_window_min", [None, None])
        if a is None or b is None or not (0 <= a <= b):
            errors.append(
                f"customer {c.get('id')} has an invalid time window: "
                f"{c.get('time_window_min')}")
        x, y = c.get("x"), c.get("y")
        if not (0 <= x <= 20 and 0 <= y <= 20):
            errors.append(f"customer {c.get('id')} is outside [0, 20]: ({x}, {y})")

    d = depot
    if not (0 <= d.get("x", -1) <= 20 and 0 <= d.get("y", -1) <= 20):
        errors.append(f"depot is outside [0, 20]: ({d.get('x')}, {d.get('y')})")

    if inst.get("vehicle_count", 0) < 1:
        errors.append("vehicle_count must be at least 1")
    return errors
