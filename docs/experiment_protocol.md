# Experiment protocol

Two experiment groups, one rule set. Everything below is executable with the CLI in this
repository; nothing is measured by hand.

## 1. Design

| Group | Purpose | Stopping rule | Scenarios |
|---|---|---|---|
| Performance (`time_budget`) | Which algorithm delivers better plans under the same 30 s? | wall clock, 30 s per run | 15 (20 customers, 4 vehicles: 5 easy, 5 medium, 5 hard) |
| Scale (`fixed_work`) | How does quality and cost grow with instance size, independent of machine speed? | fixed number of work units | 9 (10/2, 20/4, 40/8 customers/vehicles, 3 each) |

Five runs per algorithm per scenario with seeds `1, 2, 3, 4, 5`: 24 x 3 x 5 = 360 runs
(225 performance + 135 scale). All runs execute serially on one machine, because concurrent runs
would distort the wall clock and contaminate the comparison.

The six public practice scenarios are **not** part of the measurement; they exist so that an
algorithm can be developed and debugged against data that looks like the real thing.

## 2. Running the practice set

```bash
make install                     # editable install, once
python -m ctai check data/practice/easy_01.json
python -m ctai demo              # all three algorithms, 2 s each

# both groups on the practice data
python -m ctai run data/practice --mode time_budget --time-limit 30 --seeds 1-5 \
    --out results/performance
python -m ctai run data/practice --mode fixed_work --work-budget 200000 --seeds 1-5 \
    --out results/scale
```

`python -m ctai run` prints one line per run and a summary table per algorithm; each run also
writes a JSON record to `--out`.

## 3. Running the formal experiment

The formal scenarios are generated with `ctai.datagen` using seeds held by the project owner and
are not committed before code freeze. Once they are released into `data/formal/`:

```bash
python scripts/run_full_suite.py \
    --performance data/formal/performance \
    --scale data/formal/scale \
    --seeds 1-5 \
    --time-limit 30 \
    --work-budget 200000 \
    --out results
```

The script refuses to start unless every scenario file validates, and prints a run count first so
a 360-run batch is never started by accident.

## 4. What is recorded

One JSON record per run, including the plan itself:

| Field | Meaning |
|---|---|
| `algorithm_id`, `scenario_id`, `seed`, `run_index`, `mode` | Identity of the run |
| `feasible`, `makespan_min`, `total_distance_km` | Outcome (null when infeasible) |
| `routes` | The best plan submitted, so any number can be re-checked offline |
| `termination`, `error` | How the run ended |
| `runtime_sec`, `work_done` | Cost |
| `submissions`, `rejections`, `improvements` | Search behaviour |
| `timestamp`, `package_version` | Provenance |

## 5. Reporting

```bash
python -m ctai evaluate results/performance --csv results/performance_summary.csv
```

The command prints a Markdown table (feasibility rate, makespan mean/median/best/worst, standard
deviation, mean distance, mean runtime, mean work) that can be pasted into the report. Figures:

```bash
pip install -e ".[plots]"
python -m ctai evaluate results/performance --plot results/figures/makespan.png
```

## 6. Fairness rules

* The same scenario file, the same seed and the same stopping rule for all three algorithms.
* No algorithm may read the hidden verification routes, or branch on `scenario_id`.
* No external optimisation solver may perform the routing decision (rules Section 2). The
  standard library is enough for everything in this repository, which keeps the machine state out
  of the measurement.
* A run that hits the safety ceiling is reported as a failure, not silently retried.
