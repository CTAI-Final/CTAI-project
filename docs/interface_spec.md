# JSON 输入输出接口说明（草案，待审核冻结）

> 对应规则文档第十一节。业务规则已确认；**代码实现前应冻结字段名、错误码和版本号**。
> 当前 `schema_version` 草案值：`"1.0"`。

## 1. 输入场景文件（instance）

采用 UTF-8 JSON。客户数量与数组长度必须一致；仓库编号固定为 0，客户编号建议为 1 至 n；
货物需求为正数且不大于 100；时间窗满足 0 ≤ a ≤ b。

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | string | 接口版本，如 `"1.0"` |
| `scenario_id` | string | 唯一场景编号，如 `"example_001"` |
| `depot` | object | `{"id": 0, "x": 10, "y": 10}`，仓库 |
| `customer_count` | int | 客户数量 |
| `vehicle_count` | int | 最多可用车辆数量（允许闲置） |
| `vehicle_capacity_kg` | number | 统一载重上限（100） |
| `speed_km_per_min` | number | 固定速度（0.5 公里/分钟） |
| `service_time_min` | number | 统一客户服务时长（5 分钟） |
| `customers` | array | 每项：`id, x, y, demand_kg, time_window_min` |

### 示例（两客户演示，不属于正式测试场景）

```json
{
  "schema_version": "1.0", "scenario_id": "example_001",
  "depot": {"id": 0, "x": 10, "y": 10},
  "customer_count": 2, "vehicle_count": 1,
  "vehicle_capacity_kg": 100, "speed_km_per_min": 0.5,
  "service_time_min": 5,
  "customers": [
    {"id": 1, "x": 13, "y": 10, "demand_kg": 20, "time_window_min": [0, 30]},
    {"id": 2, "x": 13, "y": 14, "demand_kg": 30, "time_window_min": [0, 40]}
  ]
}
```

计算核对：0→1 距离 3 公里、行驶 6 分钟，服务后为第 11 分钟；1→2 距离 4 公里、行驶 8 分钟，
第 19 分钟到达，服务后为第 24 分钟；2→0 距离 5 公里、行驶 10 分钟；
全部任务完成时间 34 分钟，总行驶距离 12 公里。

## 2. 输出结果文件（run result）

算法只向公共接口提交 `routes`；元数据、计时和校验结果由公共测试程序填充。
算法自行报告的时间不作为权威评价值。

| 字段 | 含义 |
|---|---|
| `schema_version` / `scenario_id` | 接口版本与场景编号 |
| `algorithm_id` | 算法标识，如 `"solver_a"` |
| `seed` / `run_index` | 随机种子与第几次运行（1–5） |
| `experiment_mode` | `"time_budget"` 或 `"fixed_work"` |
| `time_limit_sec` | 性能模式求解上限（30） |
| `work_budget` / `work_done` / `work_completed` / `safety_limit_sec` | 仅规模模式 |
| `termination` | `completed` / `timeout` / `error`；规模组额外 `safety_timeout` |
| `feasible` | 是否存在合法路线（与 `work_completed` 互相独立） |
| `routes` | 每辆使用车辆一条路线 `{"vehicle_id": k, "stops": [0, ..., 0]}` |
| `solver_runtime_sec` | 求解耗时（公共测试程序计时） |
| `makespan_min` / `total_distance_km` | 完成时间与总距离（检查器计算） |
| `validation_errors` | 检查器错误列表；空数组表示合法 |

```json
{
  "schema_version": "1.0", "scenario_id": "example_001",
  "algorithm_id": "solver_a", "seed": 1, "run_index": 1,
  "experiment_mode": "time_budget", "time_limit_sec": 30,
  "termination": "completed", "feasible": true,
  "routes": [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}],
  "solver_runtime_sec": 0.12,
  "makespan_min": 34.0, "total_distance_km": 12.0,
  "validation_errors": []
}
```

约定：

- 无合法路线时质量指标（`makespan_min`、`total_distance_km`）为 `null`，不得使用 NaN / Infinity。
- 性能组超时且有合法快照可计为成功；规模组安全超时即便有合法路线也不计为完整计时样本。
- 每辆使用车辆一条路线，闲置车辆省略。

## 3. 算法函数签名（建议）

```python
solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None
```

- `run_config` 两种模式：
  - `{"mode": "time_budget", "time_limit_sec": 30}`
  - `{"mode": "fixed_work", "work_budget": <由算法定义>, "safety_limit_sec": <待审核>}`
- `submit_solution(routes)`：算法在运行中可多次调用，公共接口保存当前最好合法方案；
  超时采用截止前已保存的最佳方案。
- 固定工作量的具体字段随算法定义（如迭代数、邻域尝试次数、种群×代数），
  须在 `algorithms/<solver>/README.md` 中说明计数口径与重试上限。
