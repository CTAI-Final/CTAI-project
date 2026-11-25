#!/usr/bin/env python
"""Build the standalone CTAI route replay from local formal experiment records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctai.checker import RouteReport, evaluate_routes  # noqa: E402
from ctai.evaluation.statistics import load_results  # noqa: E402
from ctai.instance import load_instance  # noqa: E402
from ctai.problem import Problem  # noqa: E402

ALGORITHMS = ("regret_insertion", "simulated_annealing", "tabu_search")
PERFORMANCE_SCENARIOS = (
    "perf_easy_01",
    "perf_easy_02",
    "perf_easy_03",
    "perf_easy_04",
    "perf_medium_01",
    "perf_medium_03",
    "perf_medium_04",
    "perf_hard_04",
)
SCALE_SCENARIOS = tuple(f"scale_{size}_{index:02d}" for size in (10, 20, 40) for index in range(1, 4))
ABNORMAL = {"error", "safety_limit", "safety_timeout"}
TEMPLATE = Path(__file__).with_name("route_demo_template.html")
DATA_MARKER = "__CTAI_ROUTE_DATA__"


def route_timeline(route: RouteReport, problem: Problem) -> dict:
    """Use the checker's service start times and the solver's travel model."""
    starts = iter(route.service_start)
    legs = []
    depart = 0.0
    for origin, target in zip(route.stops, route.stops[1:]):
        arrive = depart + problem.distance(origin, target) / problem.speed
        start = next(starts) if target else arrive
        end = start + problem.service_time if target else arrive
        legs.append({"from": origin, "to": target, "depart": depart,
                     "arrive": arrive, "start": start, "end": end})
        depart = end

    if not isclose(depart, route.completion_min, abs_tol=1e-6):
        raise ValueError(f"{problem.scenario_id}, vehicle {route.vehicle_id}: timeline mismatch")

    return {
        "vehicle": route.vehicle_id,
        "load": route.load_kg,
        "distance": route.distance_km,
        "completion": route.completion_min,
        "legs": legs,
    }


def prepare_run(record: dict, instance: dict, problem: Problem) -> dict:
    seed = record["seed"]
    if record.get("termination") in ABNORMAL or record.get("error"):
        return {"seed": seed, "status": "abnormal"}
    if not record["feasible"]:
        return {"seed": seed, "status": "no-solution"}

    checked = evaluate_routes(instance, record["routes"], problem)
    if (
        not checked.feasible
        or not isclose(checked.makespan_min, record["makespan_min"], abs_tol=1e-6)
        or not isclose(checked.total_distance_km, record["total_distance_km"], abs_tol=1e-6)
    ):
        raise ValueError(f"{record['scenario_id']}, {record['algorithm_id']}, seed {seed}: invalid result")

    return {
        "seed": seed,
        "status": "feasible",
        "makespan": checked.makespan_min,
        "distance": checked.total_distance_km,
        "vehicles": [route_timeline(route, problem) for route in checked.routes],
    }


def prepare_scenario(instance: dict, records: dict[str, list[dict]]) -> dict:
    problem = Problem(instance)
    depot = instance["depot"]
    points = [{"id": 0, "x": 0, "y": 0}]
    for customer in instance["customers"]:
        points.append({
            "id": customer["id"],
            "x": customer["x"] - depot["x"],
            "y": customer["y"] - depot["y"],
            "demand": customer["demand_kg"],
            "window": customer["time_window_min"],
        })

    algorithms = {}
    for algorithm in ALGORITHMS:
        source = sorted(records.get(algorithm, []), key=lambda r: r["run_index"])
        if not source or len({r["seed"] for r in source}) != len(source):
            raise ValueError(f"{problem.scenario_id}, {algorithm}: missing runs or duplicate seeds")

        runs = [prepare_run(record, instance, problem) for record in source]
        feasible = [run for run in runs if run["status"] == "feasible"]
        best = min(feasible, key=lambda r: (r["makespan"], r["distance"]), default=None)
        algorithms[algorithm] = {
            "runs": runs,
            "successes": len(feasible),
            "bestSeed": best["seed"] if best else None,
        }

    return {
        "id": instance["scenario_id"],
        "customers": instance["customer_count"],
        "vehicles": instance["vehicle_count"],
        "capacity": instance["vehicle_capacity_kg"],
        "points": points,
        "algorithms": algorithms,
    }


def prepare_group(instances: Path, results: Path, scenario_ids: tuple[str, ...], mode: str) -> list[dict]:
    wanted = set(scenario_ids)
    records = defaultdict(lambda: defaultdict(list))
    for record in load_results(results):
        scenario = record["scenario_id"]
        algorithm = record["algorithm_id"]
        if scenario in wanted and algorithm in ALGORITHMS:
            if record.get("mode") != mode:
                raise ValueError(f"{scenario}: expected {mode} result")
            records[scenario][algorithm].append(record)

    scenarios = []
    for scenario in scenario_ids:
        instance = load_instance(instances / f"{scenario}.json")
        if instance["scenario_id"] != scenario:
            raise ValueError(f"{scenario}: scenario filename and ID disagree")
        scenarios.append(prepare_scenario(instance, records[scenario]))
    return scenarios


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=Path, default=ROOT / "data" / "formal")
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "route_demo.html")
    args = parser.parse_args(argv)

    try:
        data = {
            "performance": prepare_group(
                args.instances / "performance", args.results / "performance",
                PERFORMANCE_SCENARIOS, "time_budget",
            ),
            "scale": prepare_group(
                args.instances / "scale", args.results / "scale", SCALE_SCENARIOS, "fixed_work",
            ),
        }
        template = TEMPLATE.read_text(encoding="utf-8")
        if template.count(DATA_MARKER) != 1:
            raise ValueError("The route demo template must contain one data marker.")
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(template.replace(DATA_MARKER, payload), encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Wrote {args.out} ({len(data['performance'])} performance, {len(data['scale'])} scale scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
