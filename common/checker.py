"""Legality checker and metric computation (rules Sections 3, 4 and 8).

Checks: start and end point, customer coverage, duplicate service, vehicle count, capacity,
time windows, and the return to the depot.
Conventions: full floating-point precision internally, with tolerance TOL; rounding each leg
before accumulating is not allowed.
"""

from __future__ import annotations

from .geometry import build_distance_matrix

TOL = 1e-6


def evaluate_routes(inst: dict, routes: list[dict]) -> dict:
    """Evaluate a set of routes.

    routes: [{"vehicle_id": int, "stops": [0, c..., 0]}, ...]
    Returns {"feasible", "makespan_min", "total_distance_km", "validation_errors"}.
    """
    errors: list[str] = []
    n = inst["customer_count"]
    cap = inst["vehicle_capacity_kg"]
    speed = inst["speed_km_per_min"]
    t_service = inst["service_time_min"]
    mat = build_distance_matrix(inst)

    cust = {c["id"]: c for c in inst["customers"]}
    used_ids = [r.get("vehicle_id") for r in routes]

    # vehicle ids
    if len(set(used_ids)) != len(used_ids):
        errors.append("duplicate vehicle_id")
    if used_ids and (min(used_ids) < 1 or max(used_ids) > inst["vehicle_count"]):
        errors.append(f"vehicle_id outside 1..{inst['vehicle_count']}")

    # coverage and duplicates
    served: list[int] = []
    for r in routes:
        stops = r.get("stops", [])
        served += [s for s in stops[1:-1]]
    if sorted(served) != list(range(1, n + 1)):
        missing = sorted(set(range(1, n + 1)) - set(served))
        dup = sorted({s for s in served if served.count(s) > 1})
        if missing:
            errors.append(f"missing customers: {missing}")
        if dup:
            errors.append(f"customers served more than once: {dup}")

    makespan = 0.0
    total_dist = 0.0

    for r in routes:
        stops = r.get("stops", [])
        if len(stops) < 2 or stops[0] != 0 or stops[-1] != 0:
            errors.append(
                f"vehicle {r.get('vehicle_id')} route must start and end at depot 0")
            continue

        load = sum(cust[s]["demand_kg"] for s in stops[1:-1])
        if load > cap + TOL:
            errors.append(f"vehicle {r.get('vehicle_id')} overloaded: {load} > {cap} kg")

        t = 0.0          # departs from the depot at time 0
        last = 0
        for s in stops[1:]:
            d = mat[last][s]
            total_dist += d
            arrive = t + d / speed
            if s == 0:
                t = arrive          # back at the depot, does not depart again
            else:
                a, b = cust[s]["time_window_min"]
                start = max(arrive, a)          # early arrival waits until a
                if start > b + TOL:             # service must not start later than b
                    errors.append(
                        f"customer {s} time-window violation: "
                        f"service start {start:.6f} > {b}")
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
