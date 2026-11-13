# CTAI-project — Multi-Vehicle Delivery Route Optimisation

[![CI](https://github.com/CTAI-Final/CTAI-project/actions/workflows/ci.yml/badge.svg)](https://github.com/CTAI-Final/CTAI-project/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Course project for *Computational Thinking for AI* (Track A). Three self-implemented delivery
routing algorithms are measured against one rule set, one checker and one stopping rule, so that
"which algorithm is better" is a number and not an opinion.

The problem: 20 customers, 4 homogeneous vehicles of 100 kg, a 20 × 20 km square, service time
5 min and a time window per customer. Minimise the completion time of the whole fleet
(makespan), then the total travel distance.

## Quick start

```bash
make install                 # pip install -e .
make test                    # 43 unit tests, ~2 s
python -m ctai demo          # three algorithms, one scenario, 2 s each
```

Real output of `python -m ctai demo`:

```
demo on easy_01.json, 2 s per algorithm

greedy_insertion     easy_01        seed 1  makespan   114.08 min   distance  138.61 km  completed    work      270    0.00s
local_search         easy_01        seed 1  makespan    96.78 min   distance  139.58 km  completed    work     3835    0.03s
simulated_annealing  easy_01        seed 1  makespan    83.54 min   distance  112.41 km  time_budget  work   183290    2.00s
```

No configuration, no data download: the six practice scenarios are committed and the package has
no third-party dependency.

## Repository layout

```
docs/                     Rules, interface, experiment protocol, architecture, algorithm notes
data/practice/            Six public practice scenarios + manifest (seeds and reference values)
data/schema/              JSON Schema for a scenario file
src/ctai/
  geometry.py             Euclidean distance, distance matrix
  instance.py             Scenario loading and validation
  problem.py              Preprocessed scenario, fast route simulation
  checker.py              Rule validation and objective (the single source of truth)
  submitter.py            Submission channel, keeps the best feasible plan
  budget.py               Time budget, work counting, safety ceiling
  datagen.py              Deterministic scenario generator with a planted solution
  algorithms/             Three reference algorithms + the move operators they share
  runner/                 Run one experiment or a whole matrix, write JSON records
  evaluation/             Statistics, Markdown/CSV tables, optional figures
  cli.py                  check · solve · run · evaluate · data · demo
tests/                    43 unit tests over checker, algorithms, runner and generator
scripts/                  Regenerate practice data, run the formal experiment
results/                  Run records (ignored by git, only the directory is kept)
```

## Documentation

| Document | Content |
|---|---|
| [docs/rules.md](docs/rules.md) | The project rules (English, 16 sections) |
| [docs/interface.md](docs/interface.md) | The algorithm contract: `solve(...)`, `run_config`, submission, failure behaviour |
| [docs/experiment_protocol.md](docs/experiment_protocol.md) | Both experiment groups, seeds, reporting, fairness rules |
| [docs/architecture.md](docs/architecture.md) | Module map, data flow, design decisions, test strategy |
| [docs/algorithms/](docs/algorithms/) | One note per algorithm: idea, pseudocode, complexity, parameters, limitations |

## The three algorithms

| Id | Strategy | Random | Note |
|---|---|---|---|
| `greedy_insertion` | Sequential cheapest insertion, earliest-deadline first, no repair | no | [note](docs/algorithms/greedy_insertion.md) |
| `local_search` | Same construction + best-improvement descent over relocate / swap / 2-opt | no | [note](docs/algorithms/local_search.md) |
| `simulated_annealing` | Same construction + annealing over the same neighbourhoods, reheated | yes | [note](docs/algorithms/simulated_annealing.md) |

All three share one constructor on purpose: any difference in the results then comes from the
search strategy, not from a lucky start. Registering a fourth algorithm is two lines — see
[docs/interface.md](docs/interface.md).

## How a run is measured

```python
solve(instance, seed, run_config, submit_solution)
```

An algorithm never returns a plan and never measures itself. It submits candidate plans; the
harness validates each one, keeps the best feasible plan, and writes the record. Two stopping
rules share the same code:

| Mode | Group | Stop when |
|---|---|---|
| `time_budget` | Performance | 30 s of wall clock per run |
| `fixed_work` | Scale | A fixed number of work units (one unit = one candidate evaluation) |

The `fixed_work` mode exists so that the scale experiment does not inherit the speed of one
laptop. Both are polled through the same object, so an algorithm is written once:

```python
budget = run_config["budget"]
while not budget.expired():
    budget.spend()          # one candidate evaluation
    ...
```

## Experiment design

| Group | Configuration | Scenarios | Runs |
|---|---|---|---|
| Performance | 20 customers, 4 vehicles; 5 easy / 5 medium / 5 hard; 30 s per run | 15 | 225 |
| Scale | 10/2, 20/4, 40/8 customers/vehicles, 3 each; fixed work | 9 | 135 |

Five seeds per algorithm per scenario (360 runs), executed serially on one machine. Formal
scenarios are generated with `ctai.datagen` from seeds held by the project owner and are not
committed before code freeze; the practice set uses the same generator so algorithms are developed
against look-alike data.

```bash
# practice data, both groups
python -m ctai run data/practice --mode time_budget  --time-limit 30 --seeds 1-5 --out results/performance
python -m ctai run data/practice --mode fixed_work  --work-budget 200000 --seeds 1-5 --out results/scale

# formal data, once released
python scripts/run_full_suite.py --performance data/formal/performance --scale data/formal/scale

# tables and figures
python -m ctai evaluate results/performance --csv results/performance_summary.csv
pip install -e ".[plots]"
python -m ctai evaluate results/performance --plot results/figures/makespan.png
```

## Verify a result

Every record contains the plan it measured, so any reported number can be re-checked from the
file alone:

```bash
python -m ctai check data/practice/easy_01.json --plan results/performance/greedy_insertion__easy_01__seed1__run1.json
```

```
easy_01: 20 customers, 4 vehicles, demand 252/400 kg, latest deadline 187 min
scenario is valid
vehicle  stops                          load(kg)  dist(km)  done(min)
      1  0 2 19 16 0                        34.0     35.35      85.70
      2  0 6 5 11 8 4 14 0                  72.0     32.43      97.14
      3  0 13 15 17 7 9 0                   59.0     28.79      82.58
      4  0 12 18 10 20 3 1 0                87.0     42.04     114.08
makespan 114.08 min, total distance 138.61 km
```

## Development

```bash
make test        # unit tests
make demo        # smoke test across all algorithms
make data        # regenerate data/practice from the committed seeds
make lint        # ruff (optional, dev extra)
```

The core is standard library only, by design: the numbers in the report must not depend on a
particular NumPy or SciPy build. CI runs the test suite and a CLI smoke test on Python 3.10, 3.12
and 3.13.

## Status

- Rules v0.2 are approved; the open points from Section 15 are tracked as issues.
- Checker, runner, both stopping modes and the practice generator are implemented and tested.
- The three reference algorithms are working baselines, not final submissions: each implementer
  owns one module and its note, and may replace it entirely.
- Formal scenarios are withheld until the algorithm code is frozen.

## Licence

MIT — see [LICENSE](LICENSE).
