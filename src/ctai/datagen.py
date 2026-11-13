"""Scenario generator for the public practice set.

The generator plants a solution: customers are first grouped into spatially coherent vehicle
tours, then each time window is placed around the arrival time that tour would produce. The
resulting scenario is therefore guaranteed to have at least one feasible plan, and a solver that
fails on it is genuinely failing, not fighting an impossible instance.

Difficulty is controlled by two knobs: how wide the time windows are, and how much of the fleet
capacity the demand uses.

Formal scenarios are generated with the same code but are **not** committed — the project owner
holds them and their seeds, so nobody can tune an algorithm to the exact test data.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .problem import Problem

SCHEMA_VERSION = "1.0"
GENERATOR_VERSION = "1.0"

#: difficulty -> (window slack before arrival, window slack after arrival, demand range)
DIFFICULTIES: dict[str, tuple[int, int, tuple[int, int]]] = {
    "easy": (70, 100, (8, 18)),
    "medium": (45, 60, (9, 19)),
    "hard": (30, 38, (10, 20)),
}

#: The six public practice scenarios required by the rules (2 per difficulty).
PRACTICE_SPECS: tuple[tuple[str, int, int, str, int], ...] = (
    ("easy_01", 20, 4, "easy", 20260101),
    ("easy_02", 20, 4, "easy", 20260102),
    ("medium_01", 20, 4, "medium", 20260103),
    ("medium_02", 20, 4, "medium", 20260104),
    ("hard_01", 20, 4, "hard", 20260105),
    ("hard_02", 20, 4, "hard", 20260106),
)


def _sample_points(
    rng: random.Random, count: int, depot: tuple[float, float]
) -> list[tuple[float, float]]:
    """Uniformly scattered customers, kept at least 1 km away from the depot."""
    points: list[tuple[float, float]] = []
    while len(points) < count:
        x = round(rng.uniform(0.5, 19.5), 2)
        y = round(rng.uniform(0.5, 19.5), 2)
        if math.hypot(x - depot[0], y - depot[1]) < 1.0:
            continue
        points.append((x, y))
    return points


def _group_into_tours(
    ids: list[int],
    points: dict[int, tuple[float, float]],
    demands: dict[int, float],
    vehicle_count: int,
    capacity: float,
    depot: tuple[float, float],
) -> list[list[int]]:
    """Angular sweep, capacity aware: contiguous angular sectors become vehicle tours."""
    ordered = sorted(
        ids,
        key=lambda cid: math.atan2(points[cid][1] - depot[1], points[cid][0] - depot[0]),
    )
    tours: list[list[int]] = [[] for _ in range(vehicle_count)]
    loads = [0.0] * vehicle_count
    current = 0
    for cid in ordered:
        while current < vehicle_count - 1 and loads[current] + demands[cid] > capacity * 0.95:
            current += 1
        if loads[current] + demands[cid] > capacity:
            current = min(range(vehicle_count), key=lambda k: loads[k])
            if loads[current] + demands[cid] > capacity:
                raise ValueError("demand distribution does not fit the fleet")
        tours[current].append(cid)
        loads[current] += demands[cid]
    return [tour for tour in tours if tour]


def _order_tour(
    tour: list[int],
    points: dict[int, tuple[float, float]],
    depot: tuple[float, float],
) -> list[int]:
    """Nearest-neighbour ordering starting and ending at the depot."""
    remaining = list(tour)
    ordered: list[int] = []
    current = depot
    while remaining:
        nearest = min(
            remaining,
            key=lambda cid: math.hypot(
                points[cid][0] - current[0], points[cid][1] - current[1]
            ),
        )
        ordered.append(nearest)
        remaining.remove(nearest)
        current = points[nearest]
    return ordered


def generate(
    scenario_id: str,
    customer_count: int,
    vehicle_count: int,
    difficulty: str = "medium",
    seed: int = 1,
) -> dict:
    """Build one scenario dict with a planted feasible solution."""
    if difficulty not in DIFFICULTIES:
        raise KeyError(f"unknown difficulty '{difficulty}', expected one of {sorted(DIFFICULTIES)}")
    slack_before, slack_after, (low, high) = DIFFICULTIES[difficulty]
    rng = random.Random(seed)
    depot = (10.0, 10.0)

    coordinates = _sample_points(rng, customer_count, depot)
    ids = list(range(1, customer_count + 1))
    points = dict(zip(ids, coordinates))
    demands = {cid: float(rng.randint(low, high)) for cid in ids}

    tours = _group_into_tours(ids, points, demands, vehicle_count, 100.0, depot)
    tours = [_order_tour(tour, points, depot) for tour in tours]

    # Plant the windows around the arrival times of the generated tours.
    skeleton = {
        "schema_version": SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "depot": {"id": 0, "x": depot[0], "y": depot[1]},
        "customer_count": customer_count,
        "vehicle_count": vehicle_count,
        "vehicle_capacity_kg": 100,
        "speed_km_per_min": 0.5,
        "service_time_min": 5,
        "customers": [
            {
                "id": cid,
                "x": points[cid][0],
                "y": points[cid][1],
                "demand_kg": demands[cid],
                "time_window_min": [0, 10000],
            }
            for cid in ids
        ],
    }
    problem = Problem(skeleton)
    windows: dict[int, list[float]] = {}
    for tour in tours:
        stops = [0, *tour, 0]
        stats = problem.evaluate_path(stops)
        for cid, start in zip(tour, stats.service_start):
            jitter = rng.randint(0, max(1, slack_after // 3))
            windows[cid] = [
                max(0, round(start - slack_before + rng.randint(0, max(1, slack_before // 3)), 1)),
                round(start + slack_after - jitter, 1),
            ]

    # Rounding may have produced an empty or inverted window; widen it in that case.
    for cid, (earliest, latest) in windows.items():
        if latest <= earliest:
            windows[cid] = [max(0.0, latest - 5), latest + 5]

    for customer in skeleton["customers"]:
        customer["time_window_min"] = windows[customer["id"]]
    return skeleton


def _format_instance(instance: dict) -> str:
    """Render a scenario as JSON with one customer per line.

    Customer objects are small and highly repetitive; one line each keeps a diff on a scenario
    readable, which is why the committed files are written through this function rather than
    through a generic ``json.dump``.
    """
    depot = instance["depot"]
    lines = [
        "{",
        f'  "schema_version": "{instance["schema_version"]}",',
        f'  "scenario_id": "{instance["scenario_id"]}",',
        f'  "depot": {{"id": {depot["id"]}, "x": {depot["x"]}, "y": {depot["y"]}}},',
        f'  "customer_count": {instance["customer_count"]},',
        f'  "vehicle_count": {instance["vehicle_count"]},',
        f'  "vehicle_capacity_kg": {instance["vehicle_capacity_kg"]},',
        f'  "speed_km_per_min": {instance["speed_km_per_min"]},',
        f'  "service_time_min": {instance["service_time_min"]},',
        '  "customers": [',
    ]
    rows = []
    for customer in instance["customers"]:
        earliest, latest = customer["time_window_min"]
        rows.append(
            f'    {{"id": {customer["id"]}, "x": {customer["x"]}, "y": {customer["y"]}, '
            f'"demand_kg": {customer["demand_kg"]}, '
            f'"time_window_min": [{earliest}, {latest}]}}'
        )
    lines.append(",\n".join(rows))
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_practice_set(out_dir: str | Path = "data/practice") -> list[Path]:
    """Regenerate the six committed practice files plus a manifest with the seeds."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "note": "Public practice scenarios. Formal scenarios use the same generator with seeds held by the project owner.",
        "scenarios": [],
    }

    for scenario_id, customers, vehicles, difficulty, seed in PRACTICE_SPECS:
        instance = generate(scenario_id, customers, vehicles, difficulty, seed)
        problem = Problem(instance)
        reference = _reference_makespan(instance, problem)
        if reference is None:
            raise RuntimeError(
                f"generated scenario {scenario_id} is not solvable by the reference constructor; "
                "widen the time windows or lower the demand range"
            )

        path = out_dir / f"{scenario_id}.json"
        path.write_text(_format_instance(instance), encoding="utf-8")
        written.append(path)

        manifest["scenarios"].append(
            {
                "file": path.name,
                "scenario_id": scenario_id,
                "customer_count": customers,
                "vehicle_count": vehicles,
                "difficulty": difficulty,
                "seed": seed,
                "generator": f"datagen {GENERATOR_VERSION}",
                "reference_makespan_min": reference,
            }
        )

    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    written.append(manifest_path)
    return written


def _reference_makespan(instance: dict, problem: Problem) -> float | None:
    """Makespan of the cheapest-insertion solution, kept as a sanity anchor in the manifest."""
    from .algorithms.base import construct
    from .budget import Budget

    budget = Budget(mode="fixed_work", work_budget=10**9)
    plan = construct(problem, budget)
    return round(plan.makespan, 2) if plan.feasible else None
