# CTAI-project: Multi-Vehicle Delivery Route Optimization

Computational Thinking for AI (Track A) course project. Three **self-implemented**
delivery-optimization algorithms are compared under a common rule set for a multi-vehicle
delivery routing problem with capacity and time-window constraints.

- Project rules: [docs/rules_en.md](docs/rules_en.md) (English) · [docs/rules_zh_v0.2.md](docs/rules_zh_v0.2.md) (中文审核稿)
- Interface specification: [docs/interface_spec.md](docs/interface_spec.md)
- Practice data: [data/practice/](data/practice/)

> 中文说明见 [README_zh.md](README_zh.md)。

## Project summary

| Item | Common rule |
|---|---|
| Space and depot | 20 × 20 km square; depot has id 0 and coordinates (10, 10) |
| Vehicles | Homogeneous, 100 kg load limit, fixed speed 0.5 km per minute |
| Service | Fixed 5 minutes per customer; time windows are closed intervals |
| Primary objective | Minimize the completion time of all tasks (makespan), then total travel distance |
| Time units | Delivery times and durations in minutes; algorithm computation time in seconds |

## Two experiment groups

| Experiment group | Configuration | Scenarios |
|---|---|---|
| Constraint-difficulty group | 20 customers, 4 vehicles; 5 each for easy / medium / hard; at most 30 s per run | 15 |
| Scale group | 10 / 20 / 40 customers with 2 / 4 / 8 vehicles, 3 each; timed with a fixed amount of work | 9 |
| Public practice group | 2 each for easy / medium / hard; different from the formal data | 6 |

- 24 formal scenarios in total, 5 runs per algorithm per scenario: 360 runs
  (225 performance + 135 scale).
- Seeds `[1, 2, 3, 4, 5]` (pending review); all formal runs execute serially on one machine.

## Repository layout

```
docs/           Approved rules and the interface specification
data/practice/  Public practice JSON (6 files)
common/         Data loading, distance computation, legality checker, result submission
algorithms/     One directory per implementer (solver_a / solver_b / solver_c) with README.md
runner/         Timing, seeds, stopping control, work counting and result output for both modes
evaluation/     Statistics and visualization
results/        Formal test results (release scope set by the project owner)
```

### Who owns what

| Location | Maintainer |
|---|---|
| `docs/`, `data/`, `common/`, `runner/`, `evaluation/` | Project owner / evaluation lead |
| `algorithms/solver_a`, `solver_b`, `solver_c` | The three algorithm implementers, one directory each |

Formal scenario data and the project owner's verification routes are **not** committed to this
repository before the algorithm code is frozen.

## Common algorithm interface

```python
solve(instance, seed, run_config, submit_solution)
```

- `run_config` distinguishes `mode="time_budget"` (`time_limit_sec=30`) from
  `mode="fixed_work"` (`work_budget` and `safety_limit_sec`).
- The algorithm submits only `routes` through `submit_solution`; timing and validation are
  performed by the common test program.
- Call `submit_solution` as often as useful: the common interface keeps the best feasible
  solution seen so far and falls back to it on timeout.

## Quick start

```bash
# Checker self-tests (5 tests; the practice example must give 34 min and 12 km)
python -m unittest tests.test_checker -v

# One performance-mode solve
python -m runner.run_experiments --solver algorithms.solver_a.solver:solve \
    --instance data/practice/example_001.json --algorithm-id solver_a --seed 1 --run-index 1

# One fixed-work solve (scale mode)
python -m runner.run_experiments --solver algorithms.solver_a.solver:solve \
    --instance data/practice/example_001.json --mode fixed_work \
    --work-budget 100 --safety-limit-sec 300 --out-dir results/scale
```

Requirements: Python 3.10+, with NumPy and Matplotlib permitted; an external optimization
solver may not be used to perform the delivery optimization.

## Division of work

| Role | Responsibility |
|---|---|
| Project owner and evaluation lead | Rules and interface, scenario generation, checker and test program, unified run statistics |
| Algorithm implementers × 3 | Select one distinct algorithm each and report it; implement the core steps; submit code with README |

## Ground rules

- Formal scenarios and verification routes must not enter this repository before code freeze.
- Hard-coding routes by hidden scenario id is prohibited.
- Each `algorithms/<solver>/README.md` must state: algorithm idea, reason for the choice,
  pseudocode, theoretical complexity, parameters, random-seed handling, limitations,
  dependencies, how to run, and the behaviour of both `time_budget` and `fixed_work` modes.
- Do not modify `common/`, `runner/`, `evaluation/` or `tests/` from inside an algorithm
  directory; open a PR against the project owner instead.

## Status

The rules are a review draft (v0.2). The items listed in Section 15 of the rules are still
pending confirmation, and the interface in `docs/interface_spec.md` must be frozen before
coding starts.
