# JSON Input/Output Interface Specification (draft, to be frozen)

> Corresponds to Section 11 of the rules (`docs/rules_en.md`). The business rules are confirmed;
> **the field names, error codes and version number must be frozen before implementation.**
> Current draft `schema_version`: `"1.0"`.
>
> 中文版见 [interface_spec_zh.md](interface_spec_zh.md)。

## 1. Input scenario file (instance)

UTF-8 JSON. `customer_count` must equal the length of the `customers` array; the depot id is
fixed at 0 and customer ids run from 1 to n; demand must be positive and no greater than 100;
the time window satisfies 0 ≤ a ≤ b.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Interface version, e.g. `"1.0"` |
| `scenario_id` | string | Unique scenario id, e.g. `"example_001"` |
| `depot` | object | `{"id": 0, "x": 10, "y": 10}`, the depot |
| `customer_count` | int | Number of customers |
| `vehicle_count` | int | Maximum number of available vehicles (idle ones allowed) |
| `vehicle_capacity_kg` | number | Common load limit (100) |
| `speed_km_per_min` | number | Fixed speed (0.5 km per minute) |
| `service_time_min` | number | Common customer service time (5 minutes) |
| `customers` | array | Each item: `id, x, y, demand_kg, time_window_min` |

### Example (two-customer demonstration, not a formal test scenario)

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

Calculation check: 0→1 is 3 km (6 min of travel), service ends at minute 11; 1→2 is 4 km
(8 min), arrival at minute 19 and service ends at minute 24; 2→0 is 5 km (10 min);
completion time of all tasks is 34 minutes, total travel distance is 12 km.

## 2. Output result file (run result)

The algorithm submits only `routes` to the common interface; the metadata, timing and validation
results are filled in by the common test program. Times reported by the algorithm itself are not
authoritative evaluation values.

| Field | Meaning |
|---|---|
| `schema_version` / `scenario_id` | Interface version and scenario id |
| `algorithm_id` | Algorithm identifier, e.g. `"solver_a"` |
| `seed` / `run_index` | Random seed and run number (1–5) |
| `experiment_mode` | `"time_budget"` or `"fixed_work"` |
| `time_limit_sec` | Performance-mode solving limit (30) |
| `work_budget` / `work_done` / `work_completed` / `safety_limit_sec` | Scale mode only |
| `termination` | `completed` / `timeout` / `error`; the scale group adds `safety_timeout` |
| `feasible` | Whether a feasible route exists (independent of `work_completed`) |
| `routes` | One route per used vehicle: `{"vehicle_id": k, "stops": [0, ..., 0]}` |
| `solver_runtime_sec` | Solving time (timed by the common test program) |
| `makespan_min` / `total_distance_km` | Completion time and total distance (computed by the checker) |
| `validation_errors` | Checker error list; an empty array means feasible |

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

Conventions:

- When there is no feasible route the quality metrics (`makespan_min`, `total_distance_km`) are
  `null`; NaN and Infinity must not be used.
- A performance-group timeout with a feasible snapshot may count as a success; a scale-group
  safety timeout does not count as a complete timing sample even if a feasible route exists.
- One route per used vehicle; idle vehicles are omitted.

## 3. Algorithm function signature (suggested)

```python
solve(instance: dict, seed: int, run_config: dict, submit_solution) -> None
```

- `run_config` for the two modes:
  - `{"mode": "time_budget", "time_limit_sec": 30}`
  - `{"mode": "fixed_work", "work_budget": <defined by the algorithm>, "safety_limit_sec": <pending review>}`
- `submit_solution(routes)`: the algorithm may call it many times during a run; the common
  interface keeps the best feasible solution so far, and on timeout it falls back to the best
  solution saved before the deadline.
- The concrete fields of the fixed work follow the algorithm definition (iteration count,
  neighbourhood attempts, population × generations, ...), and the counting convention plus the
  retry cap must be documented in `algorithms/<solver>/README.md`.
