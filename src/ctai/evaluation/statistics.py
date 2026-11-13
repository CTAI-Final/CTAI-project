"""Aggregate run records into the tables used in the report.

A formal experiment produces 360 JSON records (24 scenarios x 3 algorithms x 5 seeds); nobody
reads those by hand. This module turns them into one row per algorithm with the statistics the
rules ask for: feasibility rate, makespan distribution and distance.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path


def load_results(target: str | Path) -> list[dict]:
    """Load one record, or every ``*.json`` record inside a directory."""
    target = Path(target)
    if target.is_dir():
        records = []
        for path in sorted(target.rglob("*.json")):
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict) and "algorithm_id" in payload:
                records.append(payload)
        return records
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else [payload]


def summarise(records: list[dict], group_by: tuple[str, ...] = ("algorithm_id",)) -> list[dict]:
    """One row per group with the aggregate metrics used in the report."""
    groups: dict[tuple, list[dict]] = {}
    for record in records:
        groups.setdefault(tuple(record.get(key) for key in group_by), []).append(record)

    rows = []
    for key, items in sorted(groups.items()):
        feasible = [r for r in items if r.get("feasible")]
        makespans = [r["makespan_min"] for r in feasible if r.get("makespan_min") is not None]
        distances = [r["total_distance_km"] for r in feasible if r.get("total_distance_km") is not None]
        runtimes = [r["runtime_sec"] for r in items if r.get("runtime_sec") is not None]
        works = [r["work_done"] for r in items if r.get("work_done")]

        row = {name: value for name, value in zip(group_by, key)}
        row.update(
            {
                "runs": len(items),
                "feasible": len(feasible),
                "feasible_rate": round(len(feasible) / len(items), 3) if items else 0.0,
                "makespan_mean": round(statistics.fmean(makespans), 3) if makespans else None,
                "makespan_median": round(statistics.median(makespans), 3) if makespans else None,
                "makespan_best": round(min(makespans), 3) if makespans else None,
                "makespan_worst": round(max(makespans), 3) if makespans else None,
                "makespan_stdev": (
                    round(statistics.stdev(makespans), 3) if len(makespans) > 1 else 0.0
                ),
                "distance_mean": round(statistics.fmean(distances), 3) if distances else None,
                "runtime_mean": round(statistics.fmean(runtimes), 3) if runtimes else None,
                "work_mean": round(statistics.fmean(works)) if works else None,
            }
        )
        rows.append(row)
    return rows


def to_markdown(rows: list[dict]) -> str:
    """Render summary rows as a Markdown table ready to paste into the report."""
    if not rows:
        return "_no results_"
    columns = list(rows[0])
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join("" if row[c] is None else str(row[c]) for c in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def to_csv(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
