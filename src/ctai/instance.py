"""Scenario loading and input validation.

A scenario is a single JSON file. Formal scenarios are generated and held by the project owner;
the public practice scenarios in ``data/practice/`` follow exactly the same schema.

See ``docs/rules.md`` Sections 2 and 11 and ``data/schema/instance.schema.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TOL = 1e-6

REQUIRED_FIELDS = (
    "schema_version",
    "scenario_id",
    "depot",
    "customer_count",
    "vehicle_count",
    "vehicle_capacity_kg",
    "speed_km_per_min",
    "service_time_min",
    "customers",
)


def load_instance(path: str | Path) -> dict:
    """Load and validate one scenario file.

    Raises:
        ValueError: if any field is missing or inconsistent.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        instance = json.load(handle)

    errors = validate_instance(instance)
    if errors:
        joined = "\n  - ".join(errors)
        raise ValueError(f"invalid scenario {path.name}:\n  - {joined}")
    return instance


def load_instances(paths: list[str | Path]) -> list[dict]:
    """Load several scenarios, preserving order."""
    return [load_instance(p) for p in paths]


def validate_instance(instance: dict) -> list[str]:
    """Check an in-memory scenario.

    Returns:
        A list of human-readable problems; an empty list means the scenario is valid.
    """
    errors: list[str] = []

    for key in REQUIRED_FIELDS:
        if key not in instance:
            errors.append(f"missing required field '{key}'")
    if errors:
        return errors

    depot = instance["depot"]
    if depot.get("id") != 0:
        errors.append("depot id must be 0")

    customers: list[dict[str, Any]] = instance["customers"]
    count = instance["customer_count"]
    if count != len(customers):
        errors.append(
            f"customer_count is {count} but the customers array has {len(customers)} entries"
        )
    if count < 1:
        errors.append("customer_count must be at least 1")

    ids = [c.get("id") for c in customers]
    if sorted(ids) != list(range(1, len(customers) + 1)):
        errors.append(f"customer ids must be the consecutive range 1..{len(customers)}")

    capacity = instance["vehicle_capacity_kg"]
    if capacity <= 0:
        errors.append("vehicle_capacity_kg must be positive")
    if instance["vehicle_count"] < 1:
        errors.append("vehicle_count must be at least 1")
    if instance["speed_km_per_min"] <= 0:
        errors.append("speed_km_per_min must be positive")
    if instance["service_time_min"] < 0:
        errors.append("service_time_min must not be negative")

    for customer in customers:
        cid = customer.get("id")
        for field in ("x", "y", "demand_kg", "time_window_min"):
            if field not in customer:
                errors.append(f"customer {cid}: missing field '{field}'")
        if "x" in customer and not (0 <= customer["x"] <= 20):
            errors.append(f"customer {cid}: x={customer['x']} outside [0, 20]")
        if "y" in customer and not (0 <= customer["y"] <= 20):
            errors.append(f"customer {cid}: y={customer['y']} outside [0, 20]")

        demand = customer.get("demand_kg", 0)
        if not (0 < demand <= capacity + TOL):
            errors.append(f"customer {cid}: demand {demand} kg not in (0, {capacity}]")

        window = customer.get("time_window_min", [])
        if len(window) != 2:
            errors.append(f"customer {cid}: time_window_min must be [earliest, latest]")
        else:
            earliest, latest = window
            if earliest < 0 or latest < 0:
                errors.append(f"customer {cid}: time window must be non-negative")
            elif earliest > latest:
                errors.append(f"customer {cid}: earliest {earliest} later than latest {latest}")

    if not (0 <= depot.get("x", -1) <= 20 and 0 <= depot.get("y", -1) <= 20):
        errors.append(f"depot coordinates ({depot.get('x')}, {depot.get('y')}) outside [0, 20]")

    total_demand = sum(c.get("demand_kg", 0) for c in customers)
    fleet_capacity = instance["vehicle_count"] * capacity
    if total_demand > fleet_capacity + TOL:
        errors.append(
            f"total demand {total_demand} kg exceeds fleet capacity {fleet_capacity} kg"
        )
    return errors


def describe(instance: dict) -> str:
    """One-line summary used by the CLI."""
    windows = [c["time_window_min"][1] for c in instance["customers"]]
    demand = sum(c["demand_kg"] for c in instance["customers"])
    return (
        f"{instance['scenario_id']}: {instance['customer_count']} customers, "
        f"{instance['vehicle_count']} vehicles, demand {demand:.0f}/"
        f"{instance['vehicle_count'] * instance['vehicle_capacity_kg']:.0f} kg, "
        f"latest deadline {max(windows):.0f} min"
    )
