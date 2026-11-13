"""公共结果提交/保存接口（规则文档第十一节）。

算法只通过 submit_solution 提交 routes；元数据、计时与校验由公共测试程序填充。
算法自行报告的时间不作为权威评价值。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .checker import evaluate_routes


class SolutionSubmitter:
    """运行期方案提交口。

    - 性能模式：可多次调用，保存当前最好合法方案；超时取截止前最佳。
    - 规模模式：同样接受合法方案；计时按完整工作量口径由 runner 记录。
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
        self.best: dict | None = None          # 当前最好合法方案
        self.all_submissions: list[dict] = []  # 全部提交记录（供诊断）

    def submit(self, routes: list[dict]) -> dict:
        """提交一组路线；合法则更新 best，返回评估结果。"""
        result = evaluate_routes(self.inst, routes)
        result["submitted_at_sec"] = time.perf_counter()
        result["routes"] = routes
        self.all_submissions.append(result)
        if result["feasible"]:
            if (self.best is None
                    or result["makespan_min"] < self.best["makespan_min"] - 1e-6
                    or (abs(result["makespan_min"] - self.best["makespan_min"]) <= 1e-6
                        and result["total_distance_km"] < self.best["total_distance_km"] - 1e-6)):
                self.best = result
        return result

    def to_result(self, termination: str, runtime_sec: float | None = None,
                  extra: dict | None = None) -> dict:
        """生成最终结果 JSON（对应 docs/interface_spec.md 第 2 节）。"""
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
    """按 <algorithm_id>_<scenario_id>_seed<seed>_run<run_index>.json 保存。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (f"{result['algorithm_id']}_{result['scenario_id']}"
            f"_seed{result['seed']}_run{result['run_index']}.json")
    path = out_dir / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path
