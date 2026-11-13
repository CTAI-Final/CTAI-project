# Algorithm interface

This is the contract between the harness and any submitted algorithm. It is intentionally small:
an algorithm is one function that searches, and one object that accepts candidate plans.

```python
solve(instance: dict, seed: int, run_config: dict, submit_solution: SolutionSubmitter) -> None
```

| Argument | Meaning |
|---|---|
| `instance` | The scenario, already validated. Same structure as the JSON file (rules Section 11). |
| `seed` | Run seed. All randomness must be derived from this value and nothing else. |
| `run_config` | Stopping rule and mode fields, see below. |
| `submit_solution` | The only way to report a plan. Call it as often as you like. |

The function returns nothing. The harness reads the best plan from `submit_solution`.

## `run_config`

| Key | Type | Meaning |
|---|---|---|
| `mode` | `"time_budget"` \| `"fixed_work"` | Which experiment group this run belongs to. |
| `time_limit_sec` | float \| None | 30 s in the performance group, `None` under fixed work. |
| `work_budget` | int \| None | Work units allowed in the scale group, `None` under a time budget. |
| `safety_limit_sec` | float | Hard ceiling; the harness aborts the run when it is passed. |
| `seed` | int | Same value as the `seed` argument. |
| `algorithm_id` | str | Identifier used in result records. |
| `budget` | `ctai.budget.Budget` | Object you poll; see below. |

You never read the wall clock yourself. In both modes you ask the budget:

```python
budget = run_config["budget"]
while not budget.expired():
    budget.spend()          # one candidate evaluation
    ...
```

`Budget.expired()` returns `True` for both modes — when the 30 s are used up, or when the work
budget is exhausted. That is the only stopping test an algorithm needs, and it is why the same
code runs in both experiment groups.

### Work units

One unit is one candidate solution evaluation: one feasibility-plus-cost check of a complete
plan, or of one candidate insertion / move. Reading the distance matrix, computing an objective
from values already in memory, and copying a route are free. Every algorithm counts with this
same unit, so the scale group compares like with like. Document any deviation from this rule in
your algorithm note.

## `submit_solution.submit(routes)`

```python
submit_solution.submit([
    {"vehicle_id": 1, "stops": [0, 4, 7, 0]},
    {"vehicle_id": 3, "stops": [0, 2, 9, 5, 0]},
])
```

* `stops` must begin and end with depot `0`; the interior is the customers in visiting order.
* Empty vehicles may be omitted. At most `vehicle_count` entries, ids in `1..vehicle_count`.
* Every customer must appear exactly once across all routes.
* The return value is the evaluation of *this* candidate: `feasible`, `makespan_min`,
  `total_distance_km`, `validation_errors`. Infeasible candidates are counted and discarded.
* The harness keeps the best feasible plan seen so far and ranks plans by makespan first, total
  distance second.

The harness validates every submission. An algorithm cannot "win" by reporting an illegal plan,
and it cannot lose work when it is cut off mid-search: whatever it submitted last is what counts.

## Failure behaviour

| Situation | Recorded `termination` |
|---|---|
| The algorithm returns normally | `completed`, or the budget reason if it stopped at the limit |
| Time limit reached | `time_budget` |
| Work budget reached | `work_budget` |
| Safety ceiling passed | `safety_limit` (the run is aborted) |
| An exception escapes | `error`, with the type and message in `error` |
| No feasible plan submitted | `feasible: false`, `makespan_min: null` |

A crashing algorithm never stops the batch; it just loses that run.

## Registering a new algorithm

1. Put the module anywhere importable, exposing a module-level `solve`.
2. Either add it to `REGISTRY` in `src/ctai/algorithms/__init__.py`, or pass a dotted path on the
   command line: `--algorithm my_package.my_module:solve`.
3. Add `docs/algorithms/<name>.md` with the content listed in rules Section 13.
4. Add it to the CI matrix in `.github/workflows/ci.yml`.

## Minimal complete example

```python
from ctai.algorithms.base import construct

def solve(instance, seed, run_config, submit_solution):
    plan = construct(submit_solution.problem, run_config["budget"])
    submit_solution.submit(plan.payload())
```
