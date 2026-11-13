"""可视化（规则文档第九节）。出题方统一生成。

- 性能组：逐场景指标表、成功率图、配送完成时间与波动图、距离比较图；
- 规模组：客户数量与固定工作量计算耗时曲线及耗时波动，注明车辆数量、
  工作量设置、完整完成次数和截断次数；
- 保护上限终止的记录单独标注，不作为完整耗时点拟合增长趋势；
- 路线图：仓库与客户坐标、不同颜色区分车辆、标明客户编号与访问顺序；
  平均指标不对应真实路线，不得标在最佳路线图上。
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
    ax.set_ylabel("成功率")
    ax.set_title("各场景成功率（合法运行次数 / 5）")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def makespan_chart(per_scenario_mean: dict[str, float],
                   per_scenario_std: dict[str, float | None],
                   out_path: str | Path) -> Path:
    """配送完成时间与波动（误差棒为样本标准差；None 不绘制）。"""
    names = list(per_scenario_mean)
    means = [per_scenario_mean[n] for n in names]
    stds = [per_scenario_std.get(n) or 0 for n in names]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(names, means, yerr=stds, capsize=4)
    ax.set_ylabel("完成时间（分钟）")
    ax.set_title("配送完成时间与波动")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def scale_time_curve(customer_counts: list[int], mean_times: list[float],
                     std_times: list[float | None], vehicle_counts: list[int],
                     out_path: str | Path) -> Path:
    """规模组：客户数量 vs 固定工作量计算耗时曲线（注明车辆数量）。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    stds = [s or 0 for s in std_times]
    ax.errorbar(customer_counts, mean_times, yerr=stds, marker="o", capsize=4)
    for x, y, k in zip(customer_counts, mean_times, vehicle_counts):
        ax.annotate(f"{k} 车", (x, y), textcoords="offset points", xytext=(0, 8),
                    fontsize=9, ha="center")
    ax.set_xlabel("客户数量")
    ax.set_ylabel("固定工作量求解耗时（秒）")
    ax.set_title("规模实验：耗时增长曲线")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def route_plot(inst: dict, routes: list[dict], title: str,
               out_path: str | Path) -> Path:
    """单次运行的路线图（不用于平均指标）。"""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(inst["depot"]["x"], inst["depot"]["y"], marker="s", s=120,
               color="black", label="仓库 0")
    xs = [c["x"] for c in inst["customers"]]
    ys = [c["y"] for c in inst["customers"]]
    ax.scatter(xs, ys, color="lightgray", edgecolors="gray", zorder=1)
    for i, c in enumerate(inst["customers"], start=1):
        ax.annotate(str(c["id"]), (c["x"], c["y"]), fontsize=8)

    for r in routes:
        color = VEHICLE_COLORS[(r["vehicle_id"] - 1) % len(VEHICLE_COLORS)]
        stops = r["stops"]
        cx = {0: (inst["depot"]["x"], inst["depot"]["y"])}
        cx.update({c["id"]: (c["x"], c["y"]) for c in inst["customers"]})
        px = [cx[s][0] for s in stops]
        py = [cx[s][1] for s in stops]
        ax.plot(px, py, color=color, alpha=0.85,
                label=f"车辆 {r['vehicle_id']}", zorder=2)
        # 访问顺序
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
