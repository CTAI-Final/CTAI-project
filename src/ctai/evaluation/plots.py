"""Figures for the report.

Matplotlib is optional: the core package never imports it, and the repository works without it.
Install the extra with ``pip install -e ".[plots]"``.
"""

from __future__ import annotations

from pathlib import Path


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


def plot_makespan_by_scenario(records: list[dict], path: str | Path) -> Path:
    """Grouped bar chart: best makespan per scenario for each algorithm."""
    plt = _pyplot()
    scenarios = sorted({r["scenario_id"] for r in records})
    algorithms = sorted({r["algorithm_id"] for r in records})
    best = {
        (r["algorithm_id"], r["scenario_id"]): r["makespan_min"]
        for r in records
        if r.get("feasible")
    }

    width = 0.8 / max(len(algorithms), 1)
    figure, axis = plt.subplots(figsize=(max(8, 0.55 * len(scenarios) + 3), 4.2))
    for offset, algorithm in enumerate(algorithms):
        heights = [best.get((algorithm, s)) or 0 for s in scenarios]
        positions = [i + offset * width for i in range(len(scenarios))]
        axis.bar(positions, heights, width, label=algorithm)

    axis.set_ylabel("makespan (min)")
    axis.set_xlabel("scenario")
    axis.set_title("Makespan per scenario")
    axis.set_xticks([i + 0.4 - width / 2 for i in range(len(scenarios))])
    axis.set_xticklabels(scenarios, rotation=45, ha="right")
    axis.legend(fontsize=8)
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
        [r["makespan_min"] for r in records if r["algorithm_id"] == a and r.get("feasible")]
        for a in algorithms
    ]

    figure, axis = plt.subplots(figsize=(6.5, 4.0))
    axis.boxplot(data, tick_labels=algorithms)
    axis.set_ylabel("makespan (min)")
    axis.set_title("Distribution over runs")
    figure.tight_layout()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path


def plot_work_curve(records: list[dict], path: str | Path) -> Path:
    """Makespan against work done, for fixed-work runs (scale group)."""
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=(6.5, 4.0))
    for algorithm in sorted({r["algorithm_id"] for r in records}):
        points = sorted(
            (
                (r["work_done"], r["makespan_min"], r["customer_count"])
                for r in records
                if r["algorithm_id"] == algorithm
                and r.get("feasible")
                and r.get("work_done")
            ),
            key=lambda point: point[0],
        )
        if points:
            axis.plot([p[0] for p in points], [p[1] for p in points], marker="o", label=algorithm)

    axis.set_xlabel("work units")
    axis.set_ylabel("makespan (min)")
    axis.set_title("Quality against work (fixed-work runs)")
    axis.legend(fontsize=8)
    figure.tight_layout()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path
