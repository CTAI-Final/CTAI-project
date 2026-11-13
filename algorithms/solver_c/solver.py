"""solver_c 占位实现。

实现者请替换本文件。要求（规则文档第三、十一、十二节）：
- 只实现核心搜索逻辑，距离计算与合法性检查请调用 common 包；
- 通过 submitter.submit(routes) 提交方案（可多次，保留当前最好合法方案）；
- 遵守 run_config 的两种模式：time_budget（30 秒）/ fixed_work（固定工作量）；
- 随机数只从 seed 派生；
- 不读取任何隐藏验证路线，不按场景编号硬编码。
"""

from __future__ import annotations

from common.instance import load_instance
from common.solution import SolutionSubmitter


def solve(instance: dict, seed: int, run_config: dict,
          submit_solution: "SolutionSubmitter") -> None:
    """占位实现：把全部客户按编号顺序交给 1 号车（仅用于跑通流程）。

    TODO(负责人): 替换为实际算法（构造 + 改进 + 固定工作量计数）。
    """
    del seed, run_config  # 占位实现忽略；正式实现必须使用
    n = instance["customer_count"]
    routes = [{"vehicle_id": 1, "stops": [0] + list(range(1, n + 1)) + [0]}]
    submit_solution.submit(routes)
