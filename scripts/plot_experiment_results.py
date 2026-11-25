#!/usr/bin/env python
"""Generate the CTAI experiment figures from saved run records."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, stdev

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctai.evaluation.plots import (  # noqa: E402
    DIFFICULTIES,
    _pyplot,
    difficulty,
    performance_scenario_order,
    plot_makespan_by_scenario,
    plot_makespan_distribution,
)
from ctai.evaluation.statistics import load_results  # noqa: E402

ABNORMAL = {"error", "safety_limit", "safety_timeout"}
COLORS = ("#176b86", "#a14914", "#6752a2")
INK = "#182535"
MUTED = "#536274"


@dataclass(frozen=True)
class ScenarioSummary:
    runs: int
    feasible: int
    abnormal: int
    makespan: float | None
    makespan_sd: float | None
    distance: float | None


def load_group(path: Path, mode: str) -> list[dict]:
    if not path.exists():
        raise ValueError(f"Result path does not exist: {path}")
    records = load_results(path)
    if not records:
        raise ValueError(f"No result records found in {path}")
    if any(record.get("mode") != mode for record in records):
        raise ValueError(f"{path} must contain only {mode} records. Use the group directory.")
    return records


def is_normal_run(record: dict) -> bool:
    return record.get("termination") not in ABNORMAL and not record.get("error")


def summarise_scenarios(records: list[dict]) -> dict[tuple[str, str], ScenarioSummary]:
    groups = defaultdict(list)
    for record in records:
        groups[record["algorithm_id"], record["scenario_id"]].append(record)

    summaries = {}
    for key, runs in groups.items():
        normal = [r for r in runs if is_normal_run(r)]
        feasible = [r for r in normal if r.get("feasible")]
        makespans = [r["makespan_min"] for r in feasible if r.get("makespan_min") is not None]
        distances = [
            r["total_distance_km"] for r in feasible if r.get("total_distance_km") is not None
        ]
        summaries[key] = ScenarioSummary(
            runs=len(runs),
            feasible=len(feasible),
            abnormal=len(runs) - len(normal),
            makespan=fmean(makespans) if makespans else None,
            makespan_sd=stdev(makespans) if len(makespans) >= 2 else None,
            distance=fmean(distances) if distances else None,
        )
    return summaries


def algorithm_label(algorithm: str) -> str:
    return algorithm.replace("_", " ").capitalize()


def scenario_label(scenario: str) -> str:
    prefix, _, suffix = scenario.removeprefix("perf_").rpartition("_")
    if prefix in DIFFICULTIES and suffix.isdigit():
        return f"{prefix[0].upper()}{suffix}"
    if scenario.startswith("scale_"):
        return scenario.removeprefix("scale_").replace("_", "-")
    return scenario


def draw_matrix(axis, summaries, algorithms, scenarios, *, title):
    colors = []
    labels = []
    for algorithm in algorithms:
        cells = [summaries.get((algorithm, scenario)) for scenario in scenarios]
        groups = [[cell] if cell is not None else [] for cell in cells]
        groups.append([cell for cell in cells if cell is not None])
        row_values = []
        row_labels = []
        for group in groups:
            runs = sum(cell.runs for cell in group)
            feasible = sum(cell.feasible for cell in group)
            abnormal = sum(cell.abnormal for cell in group)
            row_values.append(feasible / runs if runs else float("nan"))
            if not runs:
                row_labels.append("—")
                continue
            label = f"{feasible}/{runs}" + ("*" if abnormal else "")
            row_labels.append(label)
        colors.append(row_values)
        labels.append(row_labels)

    axis.set_facecolor("#f1f4f7")
    axis.imshow(colors, cmap="Blues", vmin=0, vmax=1, aspect="auto", interpolation="none")
    axis.set_xticks(range(len(scenarios) + 1), [*map(scenario_label, scenarios), "Overall"])
    axis.set_yticks(range(len(algorithms)), list(map(algorithm_label, algorithms)))
    axis.xaxis.tick_top()
    axis.tick_params(which="both", length=0, pad=6)
    axis.set_xticks([i - 0.5 for i in range(len(scenarios) + 2)], minor=True)
    axis.set_yticks([i - 0.5 for i in range(len(algorithms) + 1)], minor=True)
    axis.grid(which="minor", color="white", linewidth=1.3)
    axis.axvline(len(scenarios) - 0.5, color="white", linewidth=3)
    for row, values in enumerate(labels):
        for column, label in enumerate(values):
            axis.text(
                column, row, label, ha="center", va="center",
                color="white" if colors[row][column] >= 0.65 else INK,
                fontsize=9, fontweight="bold" if column == len(scenarios) else "normal",
            )
    axis.set_title(title, loc="left", pad=13, fontweight="bold")


def plot_overview(plt, performance, scale, algorithms, scenarios, scale_scenarios):
    figure, axes = plt.subplots(
        3, 1, figsize=(max(12.5, len(scenarios) * 0.62 + 3), 7.5),
        gridspec_kw={"height_ratios": (1, 1, 0.76)},
    )
    draw_matrix(
        axes[0], performance, algorithms, scenarios, title="Performance · feasible runs"
    )
    draw_matrix(
        axes[1], scale, algorithms, scale_scenarios, title="Scale · feasible runs"
    )
    compared = [
        algorithm for algorithm in algorithms
        if any((algorithm, scenario) in performance for scenario in scenarios)
    ]
    common = [
        scenario for scenario in scenarios
        if all(
            (summary := performance.get((algorithm, scenario))) is not None
            and summary.makespan is not None and summary.distance is not None
            for algorithm in compared
        )
    ]
    cells = []
    for algorithm in compared:
        makespans = [performance[algorithm, s].makespan for s in common]
        distances = [performance[algorithm, s].distance for s in common]
        cells.append([
            algorithm_label(algorithm),
            f"{fmean(makespans):.2f}" if common else "—",
            f"{fmean(distances):.2f}" if common else "—",
        ])
    axes[2].axis("off")
    axes[2].set_title(
        f"Solution quality · {len(common)}/{len(scenarios)} shared performance scenarios",
        loc="left", pad=8, fontweight="bold",
    )
    table = axes[2].table(
        cellText=cells, colLabels=["Algorithm", "Mean makespan (min)", "Mean distance (km)"],
        colWidths=[0.34, 0.33, 0.33], cellLoc="left", colLoc="left", bbox=[0, 0, 1, 0.94],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor("white")
        cell.set_facecolor("#dbe7ef" if row == 0 else "#f0f4f8")
        cell.set_text_props(color=INK, fontweight="bold" if row == 0 else "normal")

    figure.suptitle("Overall algorithm performance", x=0.02, ha="left", fontweight="bold")
    figure.text(
        0.02, 0.02,
        "E/M/H = easy/medium/hard. Cell color shows the feasible share; * marks abnormal runs.\n"
        "Shared performance scenarios are equally weighted in the solution quality table.",
        color=MUTED, fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.07, 1, 0.94), h_pad=2)
    return figure


def style_axis(axis, title, ylabel):
    axis.set_title(title, loc="left", pad=14, fontweight="bold")
    axis.set_ylabel(ylabel)
    axis.set_axisbelow(True)
    axis.grid(axis="y", color="#dce4ec", linewidth=0.8)
    axis.spines[["top", "right"]].set_visible(False)


def plot_success_rate(plt, performance, algorithms, scenarios, colors):
    groups = ["overall", *dict.fromkeys(map(difficulty, scenarios))]
    figure, axis = plt.subplots(figsize=(10, 5.2))
    width = 0.76 / len(algorithms)
    for index, algorithm in enumerate(algorithms):
        for column, group in enumerate(groups):
            cells = [
                performance[algorithm, scenario] for scenario in scenarios
                if (algorithm, scenario) in performance
                and (group == "overall" or difficulty(scenario) == group)
            ]
            runs = sum(cell.runs for cell in cells)
            if not runs:
                continue
            feasible = sum(cell.feasible for cell in cells)
            abnormal = sum(cell.abnormal for cell in cells)
            position = column + width * (index - (len(algorithms) - 1) / 2)
            height = 100 * feasible / runs
            axis.bar(
                position, height, width * 0.85, color=colors[algorithm],
                label=algorithm_label(algorithm) if column == 0 else None,
            )
            axis.text(
                position, height + 2, f"{feasible}/{runs}" + ("*" if abnormal else ""),
                ha="center", va="bottom", fontsize=9, color=INK,
            )
    style_axis(axis, "Feasible solution rate", "Feasible runs (%)")
    axis.set_xticks(range(len(groups)), [group.title() for group in groups])
    axis.set(ylim=(0, 121), yticks=range(0, 101, 20))
    axis.legend(loc="upper center", ncol=min(3, len(algorithms)), frameon=False)
    figure.text(
        0.02, 0.025, "Denominator includes all recorded runs. * Includes an abnormal run; "
        "only normal feasible runs count as successes.", color=MUTED, fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.06, 1, 1))
    return figure


def plot_quality_metric(plt, performance, algorithms, scenarios, colors, *, metric):
    is_makespan = metric == "makespan"
    title = "Delivery makespan and variation" if is_makespan else "Total delivery distance"
    ylabel = "Mean makespan (min)" if is_makespan else "Mean distance (km)"
    figure, axis = plt.subplots(figsize=(max(10, len(scenarios) * 0.7 + 2.5), 5.3))
    width = 0.7 / len(algorithms)
    for index, algorithm in enumerate(algorithms):
        color = colors[algorithm]
        axis.plot([], [], "o", color=color, label=algorithm_label(algorithm))
        for column, scenario in enumerate(scenarios):
            cell = performance.get((algorithm, scenario))
            value = getattr(cell, metric, None)
            if value is None:
                continue
            position = column + width * (index - (len(algorithms) - 1) / 2)
            if is_makespan and cell.makespan_sd is not None:
                axis.errorbar(
                    position, value, yerr=cell.makespan_sd, color=color, fmt="o", capsize=3,
                )
            else:
                axis.plot(position, value, "o", color=color, mfc="white" if is_makespan else color)

    for index in range(1, len(scenarios)):
        if difficulty(scenarios[index - 1]) != difficulty(scenarios[index]):
            axis.axvline(index - 0.5, color="#ccd6e0", linewidth=1)
    style_axis(axis, title, ylabel)
    axis.set_xticks(range(len(scenarios)), list(map(scenario_label, scenarios)))
    axis.set_xlim(-0.6, len(scenarios) - 0.4)
    axis.margins(y=0.17)
    axis.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.015), ncol=min(3, len(algorithms)),
        facecolor="white", edgecolor="none", framealpha=1,
    )
    note = "E/M/H = easy/medium/hard. Means use normal feasible runs; blanks show no eligible result."
    if is_makespan:
        note += "\nBars show sample SD; hollow markers indicate too few samples for SD."
    figure.text(0.02, 0.02, note, color=MUTED, fontsize=9)
    figure.tight_layout(rect=(0, 0.085, 1, 1))
    return figure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance", type=Path, default=ROOT / "results" / "performance")
    parser.add_argument("--scale", type=Path, default=ROOT / "results" / "scale")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "figures")
    args = parser.parse_args(argv)

    try:
        performance_records = load_group(args.performance, "time_budget")
        scale_records = load_group(args.scale, "fixed_work")
    except ValueError as error:
        parser.error(str(error))

    performance = summarise_scenarios(performance_records)
    scale = summarise_scenarios(scale_records)
    scenarios = sorted(
        {scenario for _, scenario in performance}, key=performance_scenario_order,
    )
    scale_scenarios = sorted({scenario for _, scenario in scale})
    performance_algorithms = sorted({algorithm for algorithm, _ in performance})
    algorithms = sorted(set(performance_algorithms) | {algorithm for algorithm, _ in scale})
    colors = {a: COLORS[i] if i < len(COLORS) else f"C{i % 10}" for i, a in enumerate(algorithms)}

    plt = _pyplot()
    args.out.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({
        "text.color": INK, "axes.labelcolor": INK, "font.size": 10,
        "axes.prop_cycle": plt.cycler(color=COLORS),
    }):
        figures = {
            "overall_performance": plot_overview(
                plt, performance, scale, algorithms, scenarios, scale_scenarios,
            ),
            "feasible_success_rate": plot_success_rate(
                plt, performance, performance_algorithms, scenarios, colors,
            ),
            "delivery_makespan_variation": plot_quality_metric(
                plt, performance, performance_algorithms, scenarios, colors, metric="makespan",
            ),
            "total_delivery_distance": plot_quality_metric(
                plt, performance, performance_algorithms, scenarios, colors, metric="distance",
            ),
        }
        for name, figure in figures.items():
            path = args.out / f"{name}.png"
            figure.savefig(path, dpi=175)
            plt.close(figure)
            print(f"wrote {path}")

        normal_performance = [r for r in performance_records if is_normal_run(r)]
        legacy_plots = (
            (plot_makespan_by_scenario, normal_performance, "best_makespan_by_scenario.png"),
            (plot_makespan_distribution, normal_performance, "makespan_distribution.png"),
        )
        for plot, records, filename in legacy_plots:
            print(f"wrote {plot(records, args.out / filename)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
