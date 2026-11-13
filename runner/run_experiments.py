"""Unified test entry point for both modes (rules Sections 5, 11 and 13).

Performance mode:
    python -m runner.run_experiments --solver algorithms.solver_a.solver:solve \\
        --instance data/practice/example_001.json --seed 1 --run-index 1 \\
        --mode time_budget

Scale mode:
    python -m runner.run_experiments --solver algorithms.solver_a.solver:solve \\
        --instance data/practice/example_001.json --seed 1 --run-index 1 \\
        --mode fixed_work --work-budget 100 --safety-limit-sec 300

Notes:
- Preprocessing (loading, distance matrix) is not counted in the solving time;
- The solving time, termination and validation result are filled in here; times reported by the
  algorithm itself are not authoritative;
- Results are saved under the corresponding results/ subdirectory.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.geometry import build_distance_matrix          # noqa: E402
from common.instance import load_instance                  # noqa: E402
from common.solution import SolutionSubmitter, save_result  # noqa: E402
from runner.safety import RunStatus                        # noqa: E402
from runner.timing import Timer, measure                     # noqa: E402


def load_solver(spec: str):
    """Load a solver function from 'package.module:function'."""
    module_name, _, func_name = spec.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, func_name or "solve")


def run(instance_path: str, solver_spec: str, algorithm_id: str, seed: int,
        run_index: int, mode: str = "time_budget", time_limit_sec: float = 30.0,
        work_budget: int | None = None, safety_limit_sec: float | None = None,
        out_dir: str = "results/performance") -> dict:
    timings: dict[str, float] = {}

    # ---- preprocessing (not counted in the solving time) ----
    with measure(timings, "preprocess_sec"):
        inst = load_instance(instance_path)
        dist_matrix = build_distance_matrix(inst)  # preprocessing cost recorded separately

    submitter = SolutionSubmitter(inst, algorithm_id, seed, run_index, mode)
    solve_fn = load_solver(solver_spec)
    run_config = {"mode": mode}
    if mode == "time_budget":
        run_config["time_limit_sec"] = time_limit_sec
    else:
        run_config["work_budget"] = work_budget
        run_config["safety_limit_sec"] = safety_limit_sec

    # ---- solving (counted) ----
    timer = Timer()
    status = RunStatus(safety_limit_sec=safety_limit_sec,
                       work_budget=work_budget)
    timer.start()
    try:
        solve_fn(inst, seed, run_config, submitter)
        timer.stop()
        status.termination = "completed"
    except Exception as exc:  # noqa: BLE001 -- anomalies marked as failures, diagnostics kept
        timer.stop()
        status.termination = "error"
        status.error_message = f"{type(exc).__name__}: {exc}"
    # TODO(owner): wire the algorithm's WorkMeter into this entry point so that `work_done`
    # and `work_completed` are reported for the scale mode.
    status.work_done = None

    result = submitter.to_result(
        termination=status.termination,
        runtime_sec=round(timer.elapsed, 6),
        extra={"preprocess_sec": round(timings.get("preprocess_sec", 0.0), 6)},
    )
    path = save_result(result, REPO_ROOT / out_dir)
    result["_saved_to"] = str(path)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CTAI unified test entry point")
    ap.add_argument("--solver", required=True,
                    help="solver function as package.module:function")
    ap.add_argument("--instance", required=True, help="path to the scenario JSON")
    ap.add_argument("--algorithm-id", default="solver_a")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--run-index", type=int, default=1)
    ap.add_argument("--mode", choices=["time_budget", "fixed_work"],
                    default="time_budget")
    ap.add_argument("--time-limit-sec", type=float, default=30.0)
    ap.add_argument("--work-budget", type=int, default=None)
    ap.add_argument("--safety-limit-sec", type=float, default=None)
    ap.add_argument("--out-dir", default="results/performance")
    args = ap.parse_args()

    result = run(args.instance, args.solver, args.algorithm_id, args.seed,
                 args.run_index, args.mode, args.time_limit_sec,
                 args.work_budget, args.safety_limit_sec, args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
