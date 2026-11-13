# Solver A — sequential cheapest insertion

`greedy_insertion` · `src/ctai/algorithms/greedy_insertion.py`

## Algorithm idea

Build one plan from scratch. Visit the customers in earliest-deadline order; for each customer,
try every position in every vehicle and keep the feasible one that gives the smallest resulting
makespan, breaking ties by total distance. There is no improvement phase — the first decision is
final.

## Why this algorithm

It is the honest baseline. Any improvement method must beat it, and it shows how much of the
final quality comes from the construction alone. It is also the cheapest to run and fully
deterministic, which makes it the natural reference for the other two submissions.

## Pseudocode

```
order  <- customers sorted by (latest service start, earliest, id)
routes <- one empty route per vehicle
for c in order:
    best <- nothing
    for each route r, each insertion position p:
        cand <- r with c inserted at p        # 1 work unit
        if cand violates capacity or a time window: continue
        key <- (max completion over all routes, total distance)
        best <- min(best, key)
    if best is nothing:                       # no feasible slot left
        insert c at the position with the least lateness
    apply the chosen insertion
submit(routes)
```

## Complexity

With `n` customers and `k` vehicles, one insertion costs at most `O(k · n)` candidate
evaluations, and one evaluation costs `O(n)` to simulate a route:

* time: `O(n^3 · k)` in the worst case, `O(n^2 · k)` on scattered instances;
* memory: `O(n^2)` for the distance matrix, `O(n)` for the plan.

For the formal sizes (`n = 20, 40`; `k = 4, 8`) a full construction is a few hundred to a few
thousand work units, far inside either stopping rule.

## Parameters

| Parameter | Value | Note |
|---|---|---|
| Priority rule | earliest latest-start first | classic EDF rule for time windows |
| Tie-break | total distance | keeps routes short when makespan ties |
| Randomness | none | `seed` is accepted and ignored |

## Seed handling

The algorithm is deterministic: five seeds give five identical plans. The seeds are still
reported so that the experiment table is uniform across the three submissions.

## Time-budget behaviour

The construction takes milliseconds, so the 30 s limit is never reached. The algorithm submits its
single plan and returns.

## Fixed-work behaviour

Every candidate insertion costs one work unit; the loop stops as soon as `budget.expired()` is
true mid-construction. Remaining customers are then appended by nearest feasible position without
being charged, so the plan is always complete and can be scored.

## Limitations

* No backtracking: one early choice can force a long route later.
* Makespan is only evaluated greedily; a locally neutral insertion may block a much better split.
* Capacity is handled by feasibility filtering only — it never rebalances an overloaded vehicle.

These limitations are exactly what Solver B and Solver C are meant to fix, and the measured gap
on the practice set is 15–25 % of makespan.

## Dependencies and how to run

Standard library only. Uses `ctai.algorithms.base` (plan, constructor) and `ctai.budget`.

```bash
python -m ctai solve data/practice/easy_01.json -a greedy_insertion --seed 1
python -m ctai run data/practice -a greedy_insertion --mode fixed_work --work-budget 100000
```
