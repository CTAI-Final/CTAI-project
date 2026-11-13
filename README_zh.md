# CTAI-project：多车辆配送路线优化

> English version: [README.md](README.md)

Computational Thinking for AI（Track A）课程项目。比较三种**自行实现**的配送优化算法，
在统一规则下求解带容量与时间窗约束的多车辆配送路线问题。

- 项目规则：[docs/rules_zh_v0.2.md](docs/rules_zh_v0.2.md)（中文审核稿 v0.2）
- 接口规范：[docs/interface_spec_zh.md](docs/interface_spec_zh.md)（英文版见 [docs/interface_spec.md](docs/interface_spec.md)）
- 练习数据：[data/practice/](data/practice/)

## 项目摘要

| 项目 | 统一规则 |
|---|---|
| 空间与仓库 | 20 × 20 公里正方形；仓库编号 0，坐标 (10,10) |
| 车辆 | 同质车辆，载重上限 100 千克，固定速度 0.5 公里/分钟 |
| 服务 | 每客户固定服务 5 分钟；时间窗为闭区间 |
| 主目标 | 最小化**全部任务完成时间**（makespan），其次比较总行驶距离 |
| 时间单位 | 配送时刻与耗时为分钟；算法计算耗时为秒 |

## 两类实验

| 实验组 | 配置 | 场景数 |
|---|---|---|
| 约束难度组 | 20 客户、4 车辆；简单/中等/困难各 5 个；每次最多 30 秒 | 15 |
| 规模组 | 10/20/40 客户配 2/4/8 车辆，各 3 个；每算法固定工作量计时 | 9 |
| 公开练习组 | 简单/中等/困难各 2 个；与正式数据不同 | 6 |

- 正式共 24 个场景，每算法每场景 5 次，共 360 次运行（性能组 225 + 规模组 135）。
- 种子统一使用 `[1,2,3,4,5]`（待审核）；全部正式测试在同一环境串行运行。

## 目录结构

```
docs/           审核通过的规则、接口说明
data/practice/  公开练习 JSON（6 个）
common/         数据读取、距离计算、合法性检查、结果保存接口
algorithms/     三位组员各自代码（solver_a / solver_b / solver_c）与 README.md
runner/         两种模式的计时、种子、停止控制、工作量记录及结果输出
evaluation/     统计与可视化
results/        正式测试结果（发布范围由出题方安排）
```

## 算法公共接口（建议）

```python
solve(instance, seed, run_config, submit_solution)
```

- `run_config` 区分 `mode="time_budget"`（`time_limit_sec=30`）与
  `mode="fixed_work"`（`work_budget` 与 `safety_limit_sec`）。
- 算法只通过 `submit_solution` 提交 `routes`；计时与校验由公共测试程序负责。

## 分工

| 角色 | 职责 |
|---|---|
| 出题方与评估负责人 | 规则与接口、场景生成、检查器与测试程序、统一运行统计 |
| 算法实现者 ×3 | 各选一种不同算法并报备；自行实现核心步骤；提交代码与 README |

## 注意事项

- 正式 24 个场景及验证路线**不得**在算法代码冻结前提交到本仓库。
- 禁止按隐藏场景编号硬编码路线。
- README 必须包含：算法思路、选择理由、伪代码、理论复杂度、参数、
  随机种子处理、局限性、依赖与运行方式。
