"""Visualization (rules Section 9). Produced uniformly by the project owner.

- Performance group: per-scenario metric table, success-rate chart, completion-time and
  variation chart, distance comparison chart;
- Scale group: computation time for a fixed amount of work versus the number of customers, with
  its variation, stating the vehicle counts, the work setting, the number of full completions and
  the number of truncations;
- Records terminated by the safety limit are marked separately and are not used as full-time
  points when fitting a growth trend;
- Route plots: depot and customer coordinates, vehicles distinguished by colour, customer ids and
  visiting order labelled; an average metric does not correspond to a real route, so it must not
  be annotated on the best-route plot.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

VEHICLE_COLORS = ["tab:blue", "tab:orange", "tab:green", "tab:red",
                  "tab:purple", "tab:brown", "tab:pink", "tab:gray"]


def success_rate_chart(per_scenario: dict[str, float], out_path: str | Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    names = list(per_scenario)
    vals = [per_scenario[n] for n in names]
    ax.bar(names, vals)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Success rate")
    ax.set_title("Success rate per scenario (feasible runs / 5)")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def makespan_chart(per_scenario_mean: dict[str, float],
                   per_scenario_std: dict[str, float | None],
                   out_path: str | Path) -> Path:
    """Completion time and variation (error bars are sample standard deviations)."""
    names = list(per_scenario_mean)
    means = [per_scenario_mean[n] for n in names]
    stds = [per_scenario_std.get(n) or 0 for n in names]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(names, means, yerr=stds, capsize=4)
    ax.set_ylabel("Completion time (min)")
    ax.set_title("Completion time of all tasks and its variation")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def scale_time_curve(customer_counts: list[int], mean_times: list[float],
                     std_times: list[float | None], vehicle_counts: list[int],
                     out_path: str | Path) -> Path:
    """Scale group: fixed-work computation time versus the number of customers."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    stds = [s or 0 for s in std_times]
    ax.errorbar(customer_counts, mean_times, yerr=stds, marker="o", capsize=4)
    for x, y, k in zip(customer_counts, mean_times, vehicle_counts):
        ax.annotate(f"{k} vehicles", (x, y), textcoords="offset points", xytext=(0, 8),
                    fontsize=9, ha="center")
    ax.set_xlabel("Number of customers")
    ax.set_ylabel("Solving time for a fixed amount of work (s)")
    ax.set_title("Scale experiment: growth of solving time")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def route_plot(inst: dict, routes: list[dict], title: str,
               out_path: str | Path) -> Path:
    """Route plot for a single run (never used for average metrics)."""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(inst["depot"]["x"], inst["depot"]["y"], marker="s", s=120,
               color="black", label="Depot 0")
    xs = [c["x"] for c in inst["customers"]]
    ys = [c["y"] for c in inst["customers"]]
    ax.scatter(xs, ys, color="lightgray", edgecolors="gray", zorder=1)
    for c in inst["customers"]:
        ax.annotate(str(c["id"]), (c["x"], c["y"]), fontsize=8)

    for r in routes:
        color = VEHICLE_COLORS[(r["vehicle_id"] - 1) % len(VEHICLE_COLORS)]
        stops = r["stops"]
        cx = {0: (inst["depot"]["x"], inst["depot"]["y"])}
        cx.update({c["id"]: (c["x"], c["y"]) for c in inst["customers"]})
        px = [cx[s][0] for s in stops]
        py = [cx[s][1] for s in stops]
        ax.plot(px, py, color=color, alpha=0.85,
                label=f"Vehicle {r['vehicle_id']}", zorder=2)
        # visiting order
        for order, s in enumerate(stops[1:-1], start=1):
            ax.annotate(str(order), cx[s], textcoords="offset points",
                        xytext=(6, 6), fontsize=7, color=color)

    ax.set_xlim(0, 20)
    ax.set_ylim(0, 20)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
