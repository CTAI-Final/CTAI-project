"""Common result submission / saving interface (rules Section 11).

Algorithms submit routes only, through submit_solution; the metadata, timing and validation
results are filled in by the common test program. Times reported by the algorithm itself are
not authoritative evaluation values.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .checker import evaluate_routes


class SolutionSubmitter:
    """Run-time solution submission port.

    - Performance mode: may be called repeatedly; keeps the best feasible solution so far and
      falls back to the best one saved before the deadline on timeout.
    - Scale mode: also accepts feasible solutions; timing follows the complete-work convention
      and is recorded by the runner.
    """

    def __init__(self, inst: dict, algorithm_id: str, seed: int, run_index: int,
                 experiment_mode: str):
        self.inst = inst
        self.meta = {
            "schema_version": inst.get("schema_version", "1.0"),
            "scenario_id": inst["scenario_id"],
            "algorithm_id": algorithm_id,
            "seed": seed,
            "run_index": run_index,
            "experiment_mode": experiment_mode,
        }
        self.best: dict | None = None          # best feasible solution so far
        self.all_submissions: list[dict] = []  # every submission (for diagnostics)

    def submit(self, routes: list[dict]) -> dict:
        """Submit a set of routes; update `best` if feasible, and return the evaluation."""
        result = evaluate_routes(self.inst, routes)
        result["submitted_at_sec"] = time.perf_counter()
        result["routes"] = routes
        self.all_submissions.append(result)
        if result["feasible"]:
            if (self.best is None
                    or result["makespan_min"] < self.best["makespan_min"] - 1e-6
                    or (abs(result["makespan_min"] - self.best["makespan_min"]) <= 1e-6
                        and result["total_distance_km"]
                        < self.best["total_distance_km"] - 1e-6)):
                self.best = result
        return result

    def to_result(self, termination: str, runtime_sec: float | None = None,
                  extra: dict | None = None) -> dict:
        """Build the final result JSON (see Section 2 of docs/interface_spec.md)."""
        best = self.best
        out = dict(self.meta)
        out.update({
            "termination": termination,
            "feasible": bool(best),
            "routes": best.pop("routes", []) if best else [],
            "solver_runtime_sec": runtime_sec,
            "makespan_min": best["makespan_min"] if best else None,
            "total_distance_km": best["total_distance_km"] if best else None,
            "validation_errors": best["validation_errors"] if best else [],
        })
        if extra:
            out.update(extra)
        return out


def save_result(result: dict, out_dir: str | Path) -> Path:
    """Save as <algorithm_id>_<scenario_id>_seed<seed>_run<run_index>.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (f"{result['algorithm_id']}_{result['scenario_id']}"
            f"_seed{result['seed']}_run{result['run_index']}.json")
    path = out_dir / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path
