#!/usr/bin/env python
"""Run the formal experiment: both groups, every algorithm, every seed.

The formal scenarios are released by the project owner into ``data/formal/`` after code freeze.
This script validates every scenario before starting, prints the run count, and then executes the
batch serially — one machine, one process, no concurrency, so the 30 s budget means the same thing
for every algorithm.

Usage:
    python scripts/run_full_suite.py \
        --performance data/formal/performance \
        --scale data/formal/scale \
        --seeds 1-5 \
        --time-limit 30 \
        --work-budget 200000 \
        --out results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ctai.algorithms import available  # noqa: E402
from ctai.evaluation.statistics import summarise, to_csv, to_markdown  # noqa: E402
from ctai.instance import validate_instance  # noqa: E402
from ctai.runner import RunSpec, run_batch  # noqa: E402


def seeds_from(text: str) -> list[int]:
    seeds: list[int] = []
    for chunk in text.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start, end = chunk.split("-", 1)
            seeds.extend(range(int(start), int(end) + 1))
        else:
            seeds.append(int(chunk))
    return seeds


def scenario_files(directory: Path) -> list[Path]:
    if not directory.exists():
        raise SystemExit(f"scenario directory not found: {directory}")
    files = sorted(p for p in directory.glob("*.json") if p.name != "manifest.json")
    if not files:
        raise SystemExit(f"no scenario files in {directory}")
    for path in files:
        with path.open(encoding="utf-8") as handle:
            errors = validate_instance(json.load(handle))
        if errors:
            raise SystemExit(f"{path.name} is invalid: {errors}")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance", default=str(ROOT / "data" / "formal" / "performance"))
    parser.add_argument("--scale", default=str(ROOT / "data" / "formal" / "scale"))
    parser.add_argument("--seeds", default="1-5")
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--work-budget", type=int, default=200_000)
    parser.add_argument("--out", default=str(ROOT / "results"))
    parser.add_argument("--algorithms", nargs="+", default=["all"])
    parser.add_argument("--dry-run", action="store_true", help="print the plan without running")
    args = parser.parse_args()

    algorithms = available() if args.algorithms in (["all"], ["ALL"]) else args.algorithms
    seeds = seeds_from(args.seeds)
    performance = scenario_files(Path(args.performance))
    scale = scenario_files(Path(args.scale))

    specs = [
        RunSpec(
            instance_path=path,
            algorithm=algorithm,
            seed=seed,
            run_index=index,
            mode="time_budget",
            time_limit_sec=args.time_limit,
            out_dir=Path(args.out) / "performance",
        )
        for path in performance
        for algorithm in algorithms
        for index, seed in enumerate(seeds, start=1)
    ] + [
        RunSpec(
            instance_path=path,
            algorithm=algorithm,
            seed=seed,
            run_index=index,
            mode="fixed_work",
            time_limit_sec=None,
            work_budget=args.work_budget,
            out_dir=Path(args.out) / "scale",
        )
        for path in scale
        for algorithm in algorithms
        for index, seed in enumerate(seeds, start=1)
    ]

    estimated = len(specs) * (args.time_limit + 5) / 60
    print(
        f"{len(performance)} performance + {len(scale)} scale scenarios, "
        f"{len(algorithms)} algorithms, {len(seeds)} seeds -> {len(specs)} runs "
        f"(roughly {estimated:.0f} min)"
    )
    if args.dry_run:
        return 0

    records = run_batch(specs)
    rows = summarise(records)
    print()
    print(to_markdown(rows))
    csv_path = to_csv(rows, Path(args.out) / "summary.csv")
    print(f"\nwrote {csv_path}")

    failures = [r for r in records if not r["feasible"]]
    if failures:
        print(f"{len(failures)} run(s) produced no feasible plan", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
