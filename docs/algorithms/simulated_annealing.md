# Solver C — cheapest insertion plus simulated annealing

`simulated_annealing` · `src/ctai/algorithms/simulated_annealing.py`

## Algorithm idea

Start from the shared construction, then walk the neighbourhood randomly. A better move is always
accepted; a worse move is accepted with probability `exp(-Δ / T)`. The temperature `T` starts at
2 % of the initial makespan, cools geometrically per evaluated move, and is partially reheated
when it falls below 10 % of its starting value, so a long run keeps exploring instead of freezing
in the first local optimum.

## Why this algorithm

Local search is trapped by its own rule. Annealing is the smallest change that escapes: one
acceptance criterion, one temperature schedule, no extra data structure. It also has a natural
fixed-work interpretation — every evaluated neighbour is one work unit — which makes it a good
fit for the scale experiment.

## Pseudocode

```
plan  <- construct()
best  <- plan; submit(best)
T     <- 0.02 * makespan(plan)
while budget not expired:
    spend(1)
    cand <- random neighbour of plan          # 55 % relocate, 30 % swap, 15 % 2-opt
    if cand infeasible: T <- T * cooling; continue
    Δ <- energy(cand) - energy(plan)          # energy = makespan + 0.02 * distance
    if Δ <= 0 or random() < exp(-Δ / T):
        plan <- cand
        if objective(plan) < objective(best):
            best <- plan; submit(best)
    T <- T * cooling
    if T < 0.1 * T0: T <- 0.5 * T0
```

## Complexity

One iteration evaluates one neighbour in `O(n)` (simulating at most two routes). With a work
budget `W` the run is `O(W · n)` time and `O(n^2)` memory for the distance matrix. Under a 30 s
budget the number of iterations is machine dependent — which is exactly why the scale group uses
work instead of seconds.

## Parameters

| Parameter | Value | Note |
|---|---|---|
| Initial temperature | `0.02 · makespan` | about 2 minutes on the practice set |
| Cooling | `0.9993` per evaluated move | ≈ 1 000 moves to halve the temperature |
| Reheat | `0.5 · T0` when `T < 0.1 · T0` | keeps long fixed-work runs alive |
| Energy | `makespan + 0.02 · distance` | distance stays a tie-breaker, not a second objective |
| Move mix | 55 / 30 / 15 % | relocate / swap / 2-opt |

## Seed handling

`random.Random(seed)` is the only source of randomness; the move type, the route, the position
and the acceptance draw all come from that generator. Two runs with the same seed and the same
work budget produce the same plan — this is asserted in `tests/test_algorithms.py`.

## Time-budget behaviour

`budget.expired()` is polled once per iteration. Because the loop body is a single neighbour
evaluation, the overshoot past 30 s is one iteration. The best plan is submitted the moment it is
found, so a timeout never costs the incumbent.

## Fixed-work behaviour

One candidate evaluation equals one work unit, so the run ends at a whole number of moves. The
`work_done` field of the result record is therefore directly comparable with the other two
algorithms, and the scale group plots quality against it.

## Limitations

* The energy mixes makespan and distance with a fixed weight; a scenario where distance dominates
  would need a different weight.
* Small neighbourhoods only: it reorders customers within and between existing routes, it cannot
  create a fundamentally different partition except through a long chain of accepted moves.
* Temperature parameters were tuned on the practice set; the formal scenarios may need one round
  of re-tuning before the scale-group configuration is frozen.

## Dependencies and how to run

Standard library only (`math`, `random`). Uses `ctai.algorithms.base` for the plan, the
constructor and the three move operators.

```bash
python -m ctai solve data/practice/hard_01.json -a simulated_annealing --seed 1 --time-limit 10
python -m ctai run data/practice -a simulated_annealing --mode fixed_work --work-budget 200000
```
