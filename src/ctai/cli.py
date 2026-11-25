"""Command line interface: ``python -m ctai <command>``.

Commands
--------
``check``     validate a scenario file (and optionally a plan)
``solve``     run one algorithm once on one scenario
``run``       run a matrix (scenarios x algorithms x seeds)
``evaluate``  summarise stored result records
``data``      regenerate the public practice scenarios
``demo``      three algorithms, one scenario, two seconds each (smoke test)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .algorithms import available
from .checker import evaluate_routes, renders_as_table
from .datagen import write_practice_set
from .evaluation.statistics import load_results, summarise, to_csv, to_markdown
from .instance import describe, load_instance
from .runner import RunSpec, format_record, run_batch, run_once


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def _scenario_paths(target: str) -> list[Path]:
    path = Path(target)
    if path.is_dir():
        return sorted(p for p in path.glob("*.json") if p.name != "manifest.json")
    return [path]


def _seed_list(text: str) -> list[int]:
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


# -- commands -------------------------------------------------------------------------------
def cmd_check(args: argparse.Namespace) -> int:
    instance = load_instance(args.scenario)
    print(describe(instance))
    print("scenario is valid")

    if args.plan:
        with open(args.plan, encoding="utf-8") as handle:
            payload = json.load(handle)
        routes = payload.get("routes", payload) if isinstance(payload, dict) else payload
        evaluation = evaluate_routes(instance, routes)
        print(renders_as_table(evaluation))
        return 0 if evaluation.feasible else 1
    return 0


def cmd_solve(args: argparse.Namespace) -> int:
    spec = RunSpec(
        instance_path=Path(args.scenario),
        algorithm=args.algorithm,
        seed=args.seed,
        mode=args.mode,
        time_limit_sec=args.time_limit,
        work_budget=args.work_budget,
        safety_limit_sec=args.safety_limit,
        out_dir=Path(args.out) if args.out else None,
    )
    record = run_once(spec)
    print(format_record(record))
    if record["error"]:
        print(f"error: {record['error']}", file=sys.stderr)
    if record["feasible"] and args.show_routes:
        print(json.dumps(record["routes"], indent=2))
    return 0 if record["feasible"] else 1


def cmd_run(args: argparse.Namespace) -> int:
    paths = _scenario_paths(args.scenarios)
    if not paths:
        print(f"no scenario files found at {args.scenarios}", file=sys.stderr)
        return 2

    algorithms = available() if args.algorithms in (["all"], ["ALL"]) else args.algorithms
    specs = [
        RunSpec(
            instance_path=path,
            algorithm=algorithm,
            seed=seed,
            run_index=index,
            mode=args.mode,
            time_limit_sec=args.time_limit,
            work_budget=args.work_budget,
            safety_limit_sec=args.safety_limit,
            out_dir=Path(args.out),
        )
        for path in paths
        for algorithm in algorithms
        for index, seed in enumerate(_seed_list(args.seeds), start=1)
    ]

    print(
        f"{len(specs)} runs: {len(paths)} scenarios x {len(algorithms)} algorithms "
        f"x seeds {args.seeds}"
    )
    records = run_batch(specs)
    print()
    print(to_markdown(summarise(records)))

    infeasible = [r for r in records if not r["feasible"]]
    if infeasible:
        print(f"\n{len(infeasible)} run(s) produced no feasible plan", file=sys.stderr)
        return 1
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    records = load_results(args.results)
    if not records:
        print(f"no result records found at {args.results}", file=sys.stderr)
        return 2
    rows = summarise(records)
    print(to_markdown(rows))
    if args.csv:
        print(f"\nwrote {to_csv(rows, args.csv)}")
    if args.plot:
        from .evaluation import plots

        print(f"wrote {plots.plot_makespan_by_scenario(records, args.plot)}")
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    for path in write_practice_set(args.out):
        print(f"wrote {path}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    root = _repo_root()
    scenario = Path(args.scenario) if args.scenario else root / "data" / "practice" / "easy_01.json"
    if not scenario.exists():
        print(f"scenario not found: {scenario}", file=sys.stderr)
        return 2

    print(f"demo on {scenario.name}, {args.time_limit:.0f} s per algorithm\n")
    failures = 0
    for algorithm in available():
        record = run_once(
            RunSpec(
                instance_path=scenario,
                algorithm=algorithm,
                seed=1,
                mode="time_budget",
                time_limit_sec=args.time_limit,
                out_dir=None,
            )
        )
        print(format_record(record))
        failures += 0 if record["feasible"] else 1
    return 0 if failures == 0 else 1


# -- parser ---------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctai",
        description="Multi-vehicle delivery routing benchmark (CTAI course project).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"ctai {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate a scenario file")
    check.add_argument("scenario", help="path to a scenario JSON file")
    check.add_argument("--plan", help="optional plan JSON to evaluate against the scenario")
    check.set_defaults(func=cmd_check)

    solve = sub.add_parser("solve", help="run one algorithm once")
    solve.add_argument("scenario")
    solve.add_argument("-a", "--algorithm", default="simulated_annealing")
    solve.add_argument("--seed", type=int, default=1)
    solve.add_argument("--mode", choices=("time_budget", "fixed_work"), default="time_budget")
    solve.add_argument("--time-limit", type=float, default=30.0, dest="time_limit")
    solve.add_argument("--work-budget", type=int, default=None, dest="work_budget")
    solve.add_argument("--safety-limit", type=float, default=None, dest="safety_limit")
    solve.add_argument("--out", default=None, help="directory for the JSON record")
    solve.add_argument("--show-routes", action="store_true")
    solve.set_defaults(func=cmd_solve)

    run = sub.add_parser("run", help="run a matrix of algorithms and scenarios")
    run.add_argument("scenarios", help="scenario file or a directory of scenario files")
    run.add_argument("-a", "--algorithms", nargs="+", default=["all"])
    run.add_argument("--seeds", default="1-5", help="e.g. '1-5' or '1,2,3'")
    run.add_argument("--mode", choices=("time_budget", "fixed_work"), default="time_budget")
    run.add_argument("--time-limit", type=float, default=30.0, dest="time_limit")
    run.add_argument("--work-budget", type=int, default=None, dest="work_budget")
    run.add_argument("--safety-limit", type=float, default=None, dest="safety_limit")
    run.add_argument("--out", default="results/performance")
    run.set_defaults(func=cmd_run)

    evaluate = sub.add_parser("evaluate", help="summarise stored result records")
    evaluate.add_argument("results", help="result JSON file or directory")
    evaluate.add_argument("--csv", default=None)
    evaluate.add_argument("--plot", default=None, help="write a PNG figure to this path")
    evaluate.set_defaults(func=cmd_evaluate)

    data = sub.add_parser("data", help="regenerate the public practice scenarios")
    data.add_argument("--out", default="data/practice")
    data.set_defaults(func=cmd_data)

    demo = sub.add_parser("demo", help="smoke test: all algorithms on one scenario")
    demo.add_argument("--scenario", default=None)
    demo.add_argument("--time-limit", type=float, default=2.0, dest="time_limit")
    demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
