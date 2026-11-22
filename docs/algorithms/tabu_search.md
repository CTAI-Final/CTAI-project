# Tabu search with relocate, swap and 2-opt

`tabu_search` · [`src/ctai/algorithms/tabu_search.py`](../../src/ctai/algorithms/tabu_search.py)

## Algorithm idea

The objective is to minimise the latest vehicle return time, then the total distance. Start with
cheapest feasible insertion in earliest-deadline order. If a customer has no feasible position,
try again with jittered deadlines for sorting. Capacity and time windows are checked by the shared
route evaluator using the original scenario.

At each step, scan the moves below and take the best admissible neighbour. Store the plan just
left in the tabu list, with routes kept in vehicle order. A candidate may revisit a tabu plan if
it strictly improves the run's best score (the aspiration rule).

| Move | Effect |
| --- | --- |
| Relocate | Move one customer within or between routes |
| Swap | Exchange two customers on the same route or on different routes |
| 2-opt | Reverse a segment of at least three stops in one route |

Swaps already cover the reversal of two consecutive stops.

## Why this algorithm

Taking a worse feasible move lets the search leave a local minimum. Storing the whole plan also
catches cases where two move types lead back to the same routes. If the search stalls, a restart
tries a different customer order.

## Pseudocode

```text
current = build the first feasible plan, retrying with jittered deadlines
if construction fails or runs out of budget: stop
best = current
submit(best)

while budget remains:
    drop expired tabu entries
    evaluate moves while budget remains
    choose the best feasible move allowed by the tabu list or aspiration rule
    if no move is admissible:
        if the tabu list is empty: stop
        continue to the next iteration
    mark current as tabu, then apply the chosen move
    if current improves best: update best and submit it
    if 30 accepted moves pass without improvement and a restart is available:
        try one fresh construction with jittered deadlines
        if it succeeds:
            set current to the restart plan and clear the tabu list
            if current improves best: update best and submit it
```

## Complexity

For `n` customers and `k` vehicles, there are at most `O(n(n + k))` moves in one scan. The
shared operators copy the plan and simulate the changed routes, so evaluating a move takes
`O(n + k)` in the worst case. One scan costs up to `O(n(n + k)^2)`. One construction
attempt has the same upper bound, since each customer can be tried in `O(n + k)` positions.
A tabu key stores `O(n + k)` stops and route boundaries. The tenure is bounded, so total space
is `O(n^2 + k)`, including the distance matrix.

## Parameters

| Setting | Value |
| --- | --- |
| Initial construction attempts | Up to 24, including the first unjittered attempt |
| Deadline jitter for retries and restarts | Uniform from −25 to +25 min |
| Tabu tenure | Uniform integer from 5 to 9 subsequent search iterations |
| Restart trigger | 30 accepted moves without improving the best plan |
| Restart limit | 12 attempts per run, with one construction per attempt |

## Seed handling

`Random(seed)` controls deadline jitter and tabu tenure. Ties in the neighbour scan go to the
first candidate in scan order. The practice runs use seed `1`.

## Time-budget behaviour

The performance protocol gives each run 30 seconds. The solver polls the shared budget before
every evaluation. If the time limit ends a scan partway through, it can still submit an
improvement from the moves already evaluated.

## Fixed-work behaviour

One work unit is one attempted insertion or neighbour evaluation. Infeasible and tabu candidates
count, as do evaluations during initial construction and restarts. Skipped no-ops, bookkeeping
and the harness's validation of submitted plans are outside the count.

Use a target of 200,000 evaluations at every instance size and a 120-second safety ceiling. The
solver stops at the work limit and handles a partial scan in the same way as in time-budget mode.
It may finish below target if construction fails or there are no feasible moves. The harness
records a safety stop as incomplete.

## Results on the practice data

Each scenario has 20 customers and four vehicles with a 100 kg capacity each. The six runs were
sequential on Windows 11 with Python 3.14.0 and an Intel Core Ultra 9 290HX Plus. The practice
files and checker came from revision `14a8d054819a9ce099082ce7b4b2f0cd3adb9e06`. Every run
reached the fixed-work limit and its saved plan passed the checker. Runtime is wall-clock time.

| Scenario | Makespan (min) | Total distance (km) | Runtime (s) | Work units |
| --- | ---: | ---: | ---: | ---: |
| `easy_01` | 83.54 | 112.41 | 0.821 | 200,000 |
| `easy_02` | 79.28 | 106.54 | 0.829 | 200,000 |
| `medium_01` | 76.16 | 98.10 | 0.781 | 200,000 |
| `medium_02` | 71.85 | 90.92 | 0.783 | 200,000 |
| `hard_01` | 85.28 | 118.78 | 0.737 | 200,000 |
| `hard_02` | 79.19 | 102.77 | 0.739 | 200,000 |

In the vehicle tables, `0` is the depot. Distances are rounded to two decimal places for display.
Fleet totals use the unrounded distances.

### `easy_01`

| Vehicle | Stops | Load (kg) | Distance (km) | Return (min) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 0 → 20 → 10 → 12 → 18 → 13 → 0 | 68 | 28.35 | 81.69 |
| 2 | 0 → 8 → 4 → 14 → 3 → 19 → 16 → 0 | 79 | 23.36 | 76.71 |
| 3 | 0 → 7 → 15 → 17 → 2 → 9 → 0 | 62 | 28.93 | 82.87 |
| 4 | 0 → 11 → 5 → 6 → 1 → 0 | 43 | 31.77 | 83.54 |

### `easy_02`

| Vehicle | Stops | Load (kg) | Distance (km) | Return (min) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 0 → 11 → 14 → 2 → 16 → 18 → 0 | 68 | 27.03 | 79.07 |
| 2 | 0 → 6 → 12 → 20 → 1 → 3 → 17 → 0 | 79 | 24.64 | 79.28 |
| 3 | 0 → 4 → 9 → 7 → 8 → 10 → 0 | 67 | 26.32 | 77.63 |
| 4 | 0 → 13 → 15 → 19 → 5 → 0 | 53 | 28.55 | 77.10 |

### `medium_01`

| Vehicle | Stops | Load (kg) | Distance (km) | Return (min) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 0 → 7 → 6 → 5 → 8 → 11 → 0 | 79 | 25.06 | 75.12 |
| 2 | 0 → 1 → 18 → 13 → 19 → 4 → 0 | 72 | 25.58 | 76.16 |
| 3 | 0 → 3 → 12 → 14 → 15 → 2 → 0 | 69 | 24.05 | 73.10 |
| 4 | 0 → 20 → 17 → 10 → 9 → 16 → 0 | 67 | 23.41 | 72.18 |

### `medium_02`

| Vehicle | Stops | Load (kg) | Distance (km) | Return (min) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 0 → 18 → 4 → 12 → 15 → 0 | 55 | 24.65 | 69.30 |
| 2 | 0 → 10 → 9 → 20 → 16 → 14 → 0 | 72 | 23.14 | 71.28 |
| 3 | 0 → 5 → 3 → 8 → 7 → 13 → 2 → 0 | 98 | 19.71 | 69.43 |
| 4 | 0 → 1 → 6 → 17 → 19 → 11 → 0 | 66 | 23.42 | 71.85 |

### `hard_01`

| Vehicle | Stops | Load (kg) | Distance (km) | Return (min) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 0 → 15 → 4 → 1 → 8 → 5 → 7 → 0 | 90 | 26.74 | 83.49 |
| 2 | 0 → 12 → 19 → 2 → 3 → 14 → 0 | 73 | 29.91 | 84.83 |
| 3 | 0 → 20 → 11 → 10 → 0 | 47 | 34.48 | 83.97 |
| 4 | 0 → 6 → 16 → 18 → 13 → 9 → 17 → 0 | 92 | 27.64 | 85.28 |

### `hard_02`

| Vehicle | Stops | Load (kg) | Distance (km) | Return (min) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 0 → 2 → 8 → 4 → 7 → 11 → 0 | 76 | 27.10 | 79.19 |
| 2 | 0 → 16 → 13 → 19 → 17 → 12 → 5 → 0 | 89 | 20.46 | 70.91 |
| 3 | 0 → 9 → 20 → 10 → 3 → 0 | 65 | 29.59 | 79.18 |
| 4 | 0 → 18 → 14 → 15 → 6 → 1 → 0 | 83 | 25.63 | 76.27 |

## Limitations

An insertion can leave a later customer with no feasible slot. In that case the solver starts
over, up to the retry limit. The neighbourhood covers only feasible moves, so some feasible plans
may only be reachable through a restart. The results give the best plans found for one seed per
scenario.

## Dependencies and how to run

Use Python 3.10 or newer. The solver uses the standard library and the project's shared route
model, operators and checker. From the repository root, run the following in PowerShell.

```powershell
$env:PYTHONPATH = "src"
python -m ctai run data/practice -a ctai.algorithms.tabu_search:solve --mode fixed_work --work-budget 200000 --safety-limit 120 --seeds 1 --out results/tabu_practice
python -m ctai check data/practice/easy_01.json --plan results/tabu_practice/solve__easy_01__seed1__run1.json
```

On a POSIX shell, replace the first line with `export PYTHONPATH=src`. In PowerShell, if
`python` opens the Microsoft Store, replace it with `&` followed by the quoted full path to the
Python executable.

The dotted-path loader uses the function name `solve` in JSON record filenames. To run with
30 seconds per scenario, use a separate output directory.

```powershell
python -m ctai run data/practice -a ctai.algorithms.tabu_search:solve --mode time_budget --time-limit 30 --safety-limit 120 --seeds 1 --out results/tabu_time
```
