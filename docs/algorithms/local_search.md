# Solver B — cheapest insertion plus deterministic local search

`local_search` · `src/ctai/algorithms/local_search.py`

## Algorithm idea

Start from the shared construction, then descend over three neighbourhoods with
best-improvement: relocate a customer, swap two customers, reverse a segment inside one route.
Stop when no move in any neighbourhood improves the lexicographic objective (makespan, then
distance) or when the budget runs out.

## Why this algorithm

It is the standard answer to the weakness of a pure construction: the plan can be repaired
instead of accepted. It is deterministic, so it gives a clean signal — any difference from
Solver A is the value of local search alone, with no randomness involved.

## Pseudocode

```
plan <- construct()                       # shared cheapest insertion
submit(plan)
while budget not expired:
    best <- plan
    for each relocate (customer, source, target, position):
        spend(1); cand <- apply if feasible
        best <- min(best, cand)
    for each swap of two customers:
        spend(1); cand <- apply if feasible
        best <- min(best, cand)
    for each 2-opt segment in every route:
        spend(1); cand <- apply if feasible
        best <- min(best, cand)
    if best is plan: break                # local optimum
    plan <- best; submit(plan)
```

## Complexity

Per improvement round, with `n` customers and `k` vehicles:

* relocate: `O(n^2 · k)` candidate moves, each `O(n)` to evaluate;
* swap: `O(n^2)` candidate moves;
* 2-opt: `O(n^2 · k)` candidate moves.

So one full round is `O(n^3 · k)`. On the practice set the descent reaches a local optimum in
3–8 rounds and 4 000–13 000 work units.

## Parameters

| Parameter | Value | Note |
|---|---|---|
| Improvement strategy | best improvement | evaluates the whole neighbourhood before moving |
| Neighbourhoods | relocate, swap, 2-opt | applied in that order per round |
| Randomness | none | `seed` is accepted and ignored |

## Seed handling

Deterministic. The five seeds of the formal experiment produce identical plans for a given
scenario; that is reported as zero variance, not as a bug.

## Time-budget behaviour

Every candidate move costs one work unit and one feasibility check; the poll on `budget.expired()`
happens before each evaluation, so a 30 s run stops between moves, never inside one. The best
plan submitted so far is what the harness keeps.

## Fixed-work behaviour

The work budget bounds the number of candidate moves, so the run ends exactly at a neighbourhood
boundary. Work is counted per candidate move, matching the definition in `docs/interface.md`.

## Limitations

* Best improvement is expensive: one round scans the entire neighbourhood.
* It cannot leave a local optimum, and the three neighbourhoods are all "small" moves, so it
  cannot restructure a badly split set of routes.
* Intra-route 2-opt only helps when route geometry has crossings; on clustered data most rounds
  find nothing there.

Solver C addresses the first three points by accepting worsening moves.

## Dependencies and how to run

Standard library only. Uses `ctai.algorithms.base` for `Plan` and the three operators.

```bash
python -m ctai solve data/practice/medium_01.json -a local_search --seed 1
python -m ctai run data/practice -a local_search --mode fixed_work --work-budget 20000
```
