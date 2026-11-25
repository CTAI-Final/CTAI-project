"""Figures for the report.

Matplotlib is optional: the core package never imports it, and the repository works without it.
Install the extra with ``pip install -e ".[plots]"``.
"""

from __future__ import annotations

from pathlib import Path

DIFFICULTIES = ("easy", "medium", "hard")


def _pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise SystemExit(
            "matplotlib is not installed. Install the optional extra first:\n"
            '    pip install -e ".[plots]"'
        ) from exc
    return plt


def difficulty(scenario: str) -> str:
    prefix = scenario.removeprefix("perf_").split("_", 1)[0]
    return prefix if prefix in DIFFICULTIES else "other"


def performance_scenario_order(scenario: str) -> tuple[int, str]:
    return (*DIFFICULTIES, "other").index(difficulty(scenario)), scenario


def plot_makespan_by_scenario(records: list[dict], path: str | Path) -> Path:
    """Grouped bar chart: best makespan per scenario for each algorithm."""
    plt = _pyplot()
    scenarios = sorted({r["scenario_id"] for r in records}, key=performance_scenario_order)
    algorithms = sorted({r["algorithm_id"] for r in records})
    best = {}
    for record in records:
        makespan = record.get("makespan_min")
        if record.get("feasible") and makespan is not None:
            key = (record["algorithm_id"], record["scenario_id"])
            best[key] = min(makespan, best.get(key, makespan))

    width = 0.8 / max(len(algorithms), 1)
    figure, axis = plt.subplots(figsize=(max(8, 0.55 * len(scenarios) + 3), 4.2))
    for offset, algorithm in enumerate(algorithms):
        heights = [best.get((algorithm, s), float("nan")) for s in scenarios]
        positions = [i + offset * width for i in range(len(scenarios))]
        axis.bar(positions, heights, width, label=algorithm)

    axis.set_ylabel("makespan (min)")
    axis.set_xlabel("scenario")
    axis.set_title("Best feasible makespan per scenario")
    axis.set_xticks([i + 0.4 - width / 2 for i in range(len(scenarios))])
    axis.set_xticklabels(scenarios, rotation=45, ha="right")
    if algorithms:
        axis.margins(y=0.23)
        axis.legend(loc="upper center", ncol=min(len(algorithms), 3), fontsize=8, frameon=False)
    figure.tight_layout()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path


def plot_makespan_distribution(records: list[dict], path: str | Path) -> Path:
    """Box plot of makespan over all runs, one box per algorithm."""
    plt = _pyplot()
    algorithms = sorted({r["algorithm_id"] for r in records})
    data = [
        [
            r["makespan_min"] for r in records
            if r["algorithm_id"] == a and r.get("feasible") and r.get("makespan_min") is not None
        ]
        for a in algorithms
    ]

    figure, axis = plt.subplots(figsize=(6.5, 4.0))
    if algorithms:
        axis.boxplot(data)
        axis.set_xticks(range(1, len(algorithms) + 1), algorithms)
    axis.set_ylabel("makespan (min)")
    axis.set_title("Feasible makespan distribution across scenarios")
    figure.tight_layout()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path
