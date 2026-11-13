"""两种模式的统一测试入口（规则文档第五、十一、十三节）。

用法示例（性能模式）：
    python -m runner.run_experiments --solver algorithms/solver_a.solver:solve \
        --instance data/practice/example_001.json --seed 1 --run-index 1 \
        --mode time_budget

用法示例（规模模式）：
    python -m runner.run_experiments --solver algorithms/solver_a.solver:solve \
        --instance data/practice/example_001.json --seed 1 --run-index 1 \
        --mode fixed_work --work-budget 100 --safety-limit-sec 300

说明：
- 预处理（读取、距离矩阵）不计入求解耗时；
- 求解耗时、termination、校验结果由本入口填充，算法自行报告的时间不作权威值；
- 结果保存到 results/ 对应子目录。
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
    """按 'package.module:function' 加载求解函数。"""
    module_name, _, func_name = spec.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, func_name or "solve")


def run(instance_path: str, solver_spec: str, algorithm_id: str, seed: int,
        run_index: int, mode: str = "time_budget", time_limit_sec: float = 30.0,
        work_budget: int | None = None, safety_limit_sec: float | None = None,
        out_dir: str = "results/performance") -> dict:
    timings: dict[str, float] = {}

    # ---- 预处理（不计入求解耗时） ----
    with measure(timings, "preprocess_sec"):
        inst = load_instance(instance_path)
        dist_matrix = build_distance_matrix(inst)  # 预处理成本单独记录

    submitter = SolutionSubmitter(inst, algorithm_id, seed, run_index, mode)
    solve_fn = load_solver(solver_spec)
    run_config = {"mode": mode}
    if mode == "time_budget":
        run_config["time_limit_sec"] = time_limit_sec
    else:
        run_config["work_budget"] = work_budget
        run_config["safety_limit_sec"] = safety_limit_sec

    # ---- 求解（计入） ----
    timer = Timer()
    status = RunStatus(safety_limit_sec=safety_limit_sec,
                       work_budget=work_budget)
    timer.start()
    try:
        solve_fn(inst, seed, run_config, submitter)
        timer.stop()
        status.termination = "completed"
    except Exception as exc:  # noqa: BLE001 —— 异常标记为失败并保留诊断
        timer.stop()
        status.termination = "error"
        status.error_message = f"{type(exc).__name__}: {exc}"
    status.work_done = None  # 工作量计数由算法的 WorkMeter 上报（待接入）

    result = submitter.to_result(
        termination=status.termination,
        runtime_sec=round(timer.elapsed, 6),
        extra={"preprocess_sec": round(timings.get("preprocess_sec", 0.0), 6)},
    )
    path = save_result(result, REPO_ROOT / out_dir)
    result["_saved_to"] = str(path)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CTAI 统一测试入口")
    ap.add_argument("--solver", required=True,
                    help="求解函数，格式 package.module:function")
    ap.add_argument("--instance", required=True, help="场景 JSON 路径")
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
