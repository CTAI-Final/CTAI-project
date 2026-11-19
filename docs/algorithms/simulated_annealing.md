# Solver C — penalty-guided simulated annealing with restarts

`simulated_annealing` · `src/ctai/algorithms/simulated_annealing.py`

## Algorithm idea

Start from the shared cheapest-insertion plan and perform a random walk over the space of plans.
Each step proposes one random neighbour; a better neighbour is always accepted, and a worse one is
accepted with probability `exp(-Δ / T)` (the Metropolis criterion). The temperature `T` controls
how often worse moves are allowed: high `T` explores, low `T` exploits. `T` falls geometrically
during an *epoch* and is reset when the epoch ends.

Five ideas distinguish this implementation from a textbook annealer:

1. **Penalty energy instead of a feasibility wall.** Infeasible plans (late customers, overloaded
   vehicles) may be visited *during* the search. They pay a penalty proportional to the minutes
   late plus the kilograms over capacity. The penalty weight adapts: it grows while the
   current plan is infeasible and shrinks while it is feasible (Cordeau, Laporte and Mercier,
   2001). This lets the walk cut through narrow infeasible corridors between good feasible
   regions. It also means the solver can **repair** a start plan that the constructor failed to
   make feasible. **Only feasible plans are ever submitted.**
2. **An energy that has a slope.** The makespan is a maximum, so moving customers between
   non-critical routes leaves it unchanged. The energy therefore adds a small weight on the mean
   route completion time and on the total distance. These terms break ties without overriding
   the makespan.
3. **Critical-route bias.** Half of the moves take their first customer from the route that
   currently defines the makespan, which is the only route whose shortening reduces the objective.
4. **Calibrated temperature.** `T0` is not a fixed fraction of the makespan. It is computed from
   200 sampled moves so that an average uphill move is accepted with probability 0.1 at the start.
   This adapts the schedule to the scale of each scenario.
5. **Restarts from the incumbent.** At the end of each epoch, or after 10 000 moves without a new
   best, the walk jumps back to the best plan found and is reheated to a lower temperature than the
   previous epoch (×0.6, floored at 0.1 · T0). The search keeps exploring, but around a better and
   better centre.

## Why this algorithm

* Local search (Solver B) stops at the first local optimum. Simulated annealing escapes local optima
  by accepting worse moves with a probability that shrinks over time (Kirkpatrick, Gelatt and
  Vecchi, 1983).
* It is an *anytime* algorithm: it always holds a best plan and can be stopped after any move,
  which fits both the 30 s budget and the fixed-work budget without code changes.
* One step is cheap (`O(n)`), so tens of thousands of moves fit in a second. Under a fixed time,
  a cheap step means far more search than a full neighbourhood scan.
* The time-window and capacity rules make the feasible region fragmented on hard scenarios. The
  penalty energy addresses exactly that weakness, which the rejection-only annealer does not.

## Pseudocode

```
plan   <- construct()                                   # shared cheapest insertion; may be infeasible
λ      <- 3                                             # penalty weight
E(p)   =  makespan(p) + 0.02·mean_completion(p) + 0.05·distance(p) + λ·(lateness(p) + overload(p))
best   <- plan if feasible; submit(best)

# temperature calibration (200 moves, counted as work)
Δ⁺     <- mean of positive E(neighbour) - E(plan) over 200 random neighbours
T0     <- -Δ⁺ / ln(0.1);  T <- T0;  Tstart <- T0
α      <- 0.002 ^ (1 / 10 000)                          # T falls to 0.2 % of Tstart in one epoch

while not budget.expired():
    budget.spend(1)
    cand <- random_neighbour(plan)                      # 35 % relocate, 20 % swap, 15 % 2-opt,
                                                        # 15 % or-opt, 15 % 2-opt*;
                                                        # first customer from the makespan route w.p. 0.5
    Δ <- E(cand) - E(plan)                              # only the 1–2 changed routes are re-simulated
    if Δ ≤ 0 or U(0,1) < exp(-Δ / T):
        plan <- cand
        if plan feasible and (makespan, distance)(plan) < (makespan, distance)(best):
            best <- plan; submit(best)
    every 100 moves: λ <- λ·1.2 if plan infeasible else λ/1.2   (clamped to [0.5, 1000])
    T <- α·T
    if 10 000 moves in this epoch or 10 000 moves since the last new best:
        plan <- best;  Tstart <- max(0.1·T0, 0.6·Tstart);  T <- Tstart
```

### Neighbourhoods

| Move | Effect | Routes touched |
|---|---|---|
| relocate | move one customer to any position of any route (an empty route opens a vehicle) | 1–2 |
| swap | exchange two customers, within one route or between two | 1–2 |
| 2-opt | reverse a segment inside one route | 1 |
| or-opt | move a chain of 2–3 consecutive customers, keeping their order | 1–2 |
| 2-opt* | exchange the tails of two routes; with an empty route this splits a route | 2 |

## Complexity

Variables: `n` customers, `k` vehicles (`k = n/5` in the scale group), `W` work budget (moves),
`I` number of improvements of the best plan (`I ≪ W`), `E = 10 000` epoch length.

| Step | Executions | Cost each | Total |
|---|---|---|---|
| Distance matrix (shared preprocessing, not timed) | 1 | `O(n²)` | `O(n²)` |
| Construction (shared constructor) | `n` insertions × `O(n + k)` positions | `O(n)` route simulation | `O(n³)` |
| Temperature calibration | 200 | `O(n + k)` | `O(n)` |
| Neighbour generation | `W` | `O(n)` list copies of at most two routes | `O(W·n)` |
| Evaluation of the changed routes | `W` | `O(n)` simulation of ≤ 2 routes | `O(W·n)` |
| Energy update, critical route | `W` | `O(k)` over cached route stats | `O(W·k)` |
| Penalty update | `W / 100` | `O(k)` | `O(W·k)` |
| Restart (copy of best) | `≤ W / E` | `O(n)` | `O(W·n / E)` |
| Submission of a new best | `I` | `O(n)` copy + `O(n)` checker | `O(I·n)` |

**Overall time:** `O(n³ + W·(n + k)) = O(n³ + W·n)`. For a fixed `W` that is much larger than
`n²`, the search term `O(W·n)` dominates. **Memory:** `O(n²)` for the shared distance matrix, plus
`O(n)` for the current, candidate and best plans.

**Scale observation (practice machine, 200 000 work units, 3 seeds, generated medium scenarios):**
about 0.9 s at 10/2, 1.0 s at 20/4 and 1.2 s at 40/8. Growth is much flatter than the linear
`O(n)` factor suggests. At these sizes most of the cost per move is a constant Python overhead
(random draws, function calls, building a small dict), and route lengths stay around `n/k ≈ 5`
because `k` grows with `n`. A single move therefore simulates routes of roughly constant length.
The theoretical `O(n)` bound is the worst case, where one route holds most customers. Three scales
alone cannot prove an asymptotic order (rules Section 10).

## Parameters

All parameters live in the frozen dataclass `Parameters` at the top of the module and are the
same in both modes and at every scale.

| Parameter | Value | Role |
|---|---|---|
| `distance_weight` | 0.05 min/km | distance as a secondary term in the energy |
| `spread_weight` | 0.02 | mean route completion; gives non-critical moves a slope |
| `penalty_initial` / `min` / `max` | 3 / 0.5 / 1000 | weight of (minutes late + kg overloaded) |
| `penalty_factor`, `penalty_period` | 1.2, every 100 moves | adaptive penalty update |
| `calibration_moves` | 200 | sample size used to compute `T0` |
| `initial_acceptance` | 0.1 | probability of accepting an average uphill move at `T0` |
| `epoch_moves` | 10 000 | length of one cooling cycle |
| `final_ratio` | 0.002 | `T` at the end of an epoch relative to its start |
| `reheat_decay`, `reheat_floor` | 0.6, 0.1 · `T0` | start temperature of the next epoch |
| `stall_moves` | 10 000 | restart early if the best has not improved for this long |
| move mix | 35 / 20 / 15 / 15 / 15 % | relocate / swap / 2-opt / or-opt / 2-opt* |
| `p_critical` | 0.5 | probability that a move starts on the makespan route |

**Tuning (practice data only, 5 seeds, fixed work):**

* A strong penalty (initial 100) was clearly worse, with a mean makespan about 6 min higher. Too weak a
  penalty (initial 1) was worse at small budgets. 3 was the best compromise.
* Removing the critical-route bias cost about 1.3 min on average.
* Lowering the initial acceptance from 0.4 to 0.1 and shortening the epoch from 30 000 to 10 000
  moves gave the largest gain.

No formal data were used for tuning.

## Seed handling

`random.Random(seed)` is created once in `solve` and is the only source of randomness. It decides
the move type, the routes, the positions, the calibration sample and every acceptance draw. The
module never reads the wall clock and never uses the global `random` state. Under `fixed_work`,
the same seed and work budget therefore produce the same plan, as asserted by
`tests/test_algorithms.py::test_seeded_runs_are_reproducible`. Under `time_budget`, the
*sequence* of moves for a seed is identical, but how far along it the run gets depends on machine
speed.

## Time-budget behaviour (performance group, 30 s)

* `budget.expired()` is polled once per move. A move costs microseconds, so the overshoot past the
  limit is negligible.
* Every new best feasible plan is submitted immediately, so a timeout never loses the incumbent.
* About 190 000 moves per second fit on the development machine for 20 customers, which is
  roughly 5–6 million moves in 30 s. That is hundreds of epochs, so the restart mechanism matters
  much more here than in a short run.

## Fixed-work behaviour (scale group)

* **Work unit:** one *proposed neighbour*. The budget is spent once per proposal, including the
  rare proposal that is discarded as degenerate (for example a relocate to the same place) before
  it is evaluated. Every loop iteration therefore consumes exactly one unit and the run cannot
  loop without progress.
* **Initialization:** the shared constructor charges one unit per candidate insertion it
  evaluates, about `n² / 2` units (270 for `easy_01`). If the budget ends during construction,
  the remaining customers are inserted without charge, as defined in `base.construct`.
* **Calibration:** at most 200 units, charged through the same budget.
* **Restarts and repair:** there is no separate restart or repair budget. A restart is a jump back
  to the incumbent, and repair happens through ordinary penalised moves, so both are paid for by
  the same per-move unit. Neither can repeat outside the budget.
* **Target:** 200 000 units at every scale (10/2, 20/4, 40/8). The target is not reduced at
  larger scales.
* **Actual work:** the harness records `work_done`. The run stops at exactly the target, unless
  the target is smaller than the construction cost. In that case the constructor finishes its
  current insertion scan first, which overshoots by at most `n + k` units.
* **Safety stop:** the harness safety ceiling aborts the run through `SafetyLimitExceeded`. The
  last submitted plan is kept, but the run is recorded as incomplete. On the practice machine a
  200 000-unit run takes about 1–1.5 s, far below any reasonable ceiling.
* Work units are this algorithm's own unit. They are **not** comparable with the units of the
  other algorithms (see `docs/algorithm_contribution_workflow.md`).

## Results on the practice data

Makespan in minutes, mean over seeds 1–5 under `fixed_work`. The best-known value is the best
makespan any run produced.

| Scenario | Construction | Reference SA, 50 k | **This SA, 50 k** | Reference SA, 200 k | **This SA, 200 k** |
|---|---|---|---|---|---|
| easy_01 | 114.08 | 83.95 | **83.57** | 83.74 | **83.54** |
| easy_02 | 96.06 | 83.06 | **80.08** | 79.28 | **79.28** |
| medium_01 | 103.20 | 76.17 | **76.17** | 76.16 | **76.16** |
| medium_02 | 104.50 | 72.02 | **71.95** | 71.85 | **71.85** |
| hard_01 | 107.15 | 88.72 | **86.55** | 86.61 | **85.28** |
| hard_02 | 101.28 | 83.10 | **79.52** | 80.29 | **79.19** |
| **mean** | 104.38 | 81.17 | **79.64** | 79.66 | **79.22** |

At 200 000 units, all five seeds reach the same, best-known plan in every scenario, so the
standard deviation is 0.

The **repair check** starts the annealer from a deliberately broken plan, with every customer on
one overloaded and late vehicle. On `hard_01`, `hard_02` and `medium_02` it returned to the
best-known feasible plan within 100 000 units. These numbers come from practice data only and do
not predict the formal results.

## Limitations

* The energy weights (distance 0.05, spread 0.02) are hand-set. In a scenario where distance and
  makespan conflict strongly, the distance term could steer the walk slightly away from the
  minimum makespan. The incumbent is always ranked by the true lexicographic objective, so this
  can only slow the search, never report a worse plan.
* Parameters were tuned on six practice scenarios with 20 customers. They may be less suitable
  for 40 customers or for formal hard data. They will be frozen before formal generation, as the
  rules require, and not retuned on formal outcomes.
* The neighbourhoods are random, so improving moves on a nearly optimal plan become rare. A
  late-stage deterministic descent could finish a run faster, but it would blur the line with
  Solver B and was deliberately left out.
* The penalty makes infeasible plans reachable. If the penalty were too weak for a scenario, the
  walk could spend long periods infeasible. The adaptive weight bounds this, but it does not
  guarantee that a feasible plan is found when the constructor fails.
* Under `time_budget`, results depend on machine speed, because the number of moves is not fixed.

## Dependencies and how to run

The module uses only the Python standard library (`math`, `random`, `dataclasses`). From the
shared code it uses `ctai.algorithms.base.construct` (the disclosed initial-solution utility) and
`ctai.problem.Problem.evaluate_path` (route simulation). The move operators, the energy, the
penalty and the schedule are all implemented in this module. It does not import the other
algorithm modules.

```bash
python -m ctai solve data/practice/hard_01.json -a simulated_annealing --seed 1 --time-limit 30
python -m ctai run data/practice -a simulated_annealing --mode time_budget --time-limit 30 --seeds 1-5 --out results/performance
python -m ctai run data/practice -a simulated_annealing --mode fixed_work --work-budget 200000 --seeds 1-5 --out results/scale
make test
```

## References

* S. Kirkpatrick, C. D. Gelatt, M. P. Vecchi. *Optimization by Simulated Annealing.* Science
  220(4598), 1983.
* J.-F. Cordeau, G. Laporte, A. Mercier. *A unified tabu search heuristic for vehicle routing
  problems with time windows.* Journal of the Operational Research Society 52, 2001. The source of
  the adaptive penalty weight.
* D. S. Johnson, C. R. Aragon, L. A. McGeoch, C. Schevon. *Optimization by Simulated Annealing: An
  Experimental Evaluation; Part I.* Operations Research 37(6), 1989. The source of calibrating
  `T0` from the acceptance rate.
* W. Michiels, E. Aarts, J. Korst. *Theoretical Aspects of Local Search.* Springer, 2007. The
  source of the convergence background and cooling schedules.
* O. Bräysy, M. Gendreau. *Vehicle Routing Problem with Time Windows, Part I: Route Construction
  and Local Search Algorithms.* Transportation Science 39(1), 2005. The source of the relocate,
  or-opt and 2-opt* neighbourhoods.
