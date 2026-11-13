"""Experiment control: one run, and a batch of runs.

The runner owns everything an algorithm must not own: loading the scenario, building the budget,
calling the algorithm, catching failures, and writing one JSON record per run. Two algorithms
measured here are therefore always measured the same way.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from ..algorithms import get_solver
from ..budget import Budget, SafetyLimitExceeded
from ..instance import load_instance
from ..submitter import SolutionSubmitter

RESULT_SUFFIX = ".json"


@dataclass
class RunSpec:
    """One measured run: one algorithm, one scenario, one seed, one stopping rule."""

    instance_path: Path
    algorithm: str = "greedy_insertion"
    seed: int = 1
    run_index: int = 1
    mode: str = "time_budget"
    time_limit_sec: float | None = 30.0
    work_budget: int | None = None
    safety_limit_sec: float | None = None
    out_dir: Path | None = Path("results/performance")
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.instance_path = Path(self.instance_path)
        if self.out_dir is not None:
            self.out_dir = Path(self.out_dir)
        if self.mode == "fixed_work" and self.work_budget is None:
            raise ValueError("fixed_work mode requires work_budget")
        if self.mode == "time_budget" and self.time_limit_sec is None:
            raise ValueError("time_budget mode requires time_limit_sec")


def run_once(spec: RunSpec) -> dict:
    """Execute one run and return its record (also written to ``spec.out_dir`` when set)."""
    instance = load_instance(spec.instance_path)
    algorithm_id, solver = get_solver(spec.algorithm)
    budget = Budget(
        mode=spec.mode,
        time_limit_sec=spec.time_limit_sec,
        work_budget=spec.work_budget,
        safety_limit_sec=spec.safety_limit_sec,
    )
    submitter = SolutionSubmitter(instance)

    run_config = {
        "mode": spec.mode,
        "time_limit_sec": budget.time_limit_sec,
        "work_budget": budget.work.budget,
        "safety_limit_sec": budget.safety_limit_sec,
        "seed": spec.seed,
        "algorithm_id": algorithm_id,
        "budget": budget,
    }

    termination = "completed"
    error: str | None = None
    try:
        solver(instance, spec.seed, run_config, submitter)
    except SafetyLimitExceeded as exc:
        termination, error = "safety_limit", str(exc)
    except Exception as exc:  # noqa: BLE001 - a broken submission must not kill the batch
        termination = "error"
        error = f"{type(exc).__name__}: {exc}"
        if spec.extra.get("traceback"):
            error += "\n" + traceback.format_exc()
    else:
        termination = budget.stop_reason() or "completed"

    record = {
        "schema_version": "1.0",
        "package_version": __version__,
        "algorithm_id": algorithm_id,
        "instance": spec.instance_path.name,
        "scenario_id": instance["scenario_id"],
        "customer_count": instance["customer_count"],
        "vehicle_count": instance["vehicle_count"],
        "seed": spec.seed,
        "run_index": spec.run_index,
        "mode": spec.mode,
        "time_limit_sec": budget.time_limit_sec,
        "work_budget": budget.work.budget,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    record.update(
        submitter.to_result(
            termination=termination,
            runtime_sec=budget.elapsed_sec,
            work_done=budget.work_done,
            error=error,
        )
    )
    if spec.extra:
        record.update({k: v for k, v in spec.extra.items() if k != "traceback"})

    if spec.out_dir is not None:
        write_result(record, spec.out_dir)
    return record


def result_filename(record: dict) -> str:
    return (
        f"{record['algorithm_id']}__{record['scenario_id']}"
        f"__seed{record['seed']}__run{record['run_index']}{RESULT_SUFFIX}"
    )


def write_result(record: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / result_filename(record)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def run_batch(specs: list[RunSpec], verbose: bool = True) -> list[dict]:
    """Run specs sequentially; a failing run is recorded, never raised."""
    records = []
    for index, spec in enumerate(specs, start=1):
        record = run_once(spec)
        records.append(record)
        if verbose:
            print(format_record(record, index, len(specs)))
    return records


def format_record(record: dict, index: int | None = None, total: int | None = None) -> str:
    prefix = f"[{index:>2}/{total}] " if index and total else ""
    if record["feasible"]:
        outcome = (
            f"makespan {record['makespan_min']:8.2f} min   "
            f"distance {record['total_distance_km']:7.2f} km"
        )
    else:
        outcome = "no feasible plan".ljust(40)
    return (
        f"{prefix}{record['algorithm_id']:<20} {record['scenario_id']:<14} "
        f"seed {record['seed']:<2} {outcome}  "
        f"{record['termination']:<12} work {record['work_done']:>8}  "
        f"{record['runtime_sec']:6.2f}s"
    )
