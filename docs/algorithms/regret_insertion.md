# Regret-k insertion

## Idea and rationale

A deterministic construction heuristic that decides both which customer to serve next and where to insert it. Unlike earliest-deadline greedy insertion, it prioritizes customers likely to lose valuable insertion opportunities. The default is regret-2; k is configurable through `run_config['regret_k']` (integer >= 2). Only Python's standard library and shared project infrastructure are used; no other algorithm module is imported.

## Definition

For each unserved customer, evaluate every insertion position in every vehicle route. Reject capacity or service-start-time violations using `Problem.evaluate_path`. Keep only the best position per vehicle. Alternatives therefore refer to distinct vehicles, not several positions within one route. Empty vehicles are separate alternatives.

Sort these options by the resulting whole-plan `(makespan, total_distance)` tuple. Let their scores be c1,...,cm, and let K = min(k, vehicle_count). Compute componentwise regret R = sum(cj - c1 for j=2,...,min(K,m)). Since the current plan is fixed during a scan, subtracting the current score to obtain insertion increments would give the same regret.

Select the customer with the largest key:

1. max(0, K-m): prioritize customers with fewer feasible vehicles than K;
2. R's makespan component, then its distance component;
3. lower best resulting makespan, then lower best distance;
4. earlier deadline, then lower customer ID.

Insert it at its best option; option ties prefer lower vehicle index and insertion position. This is a lexicographic, route-alternative regret-k adaptation for the project's makespan objective, not scalar distance-only regret. Distance regret may be negative when a higher-makespan alternative has shorter distance; it is used only after the makespan regret ties. With one vehicle, effective K is 1 and the heuristic reduces to best-score customer selection.

## Pseudocode

```
start with empty routes and all customers pending
while customers remain:
    for each pending customer:
        for every route and position:
            check budget; count one work unit; evaluate insertion
        retain the best feasible insertion per vehicle
        if no feasible option: stop without submitting a partial plan
        compute scarcity and regret priority
    insert the highest-priority customer at its best option
submit the complete feasible plan
```

## Complexity

For n customers and v vehicles, a round with t inserted customers examines (n-t)(t+v) insertions. Each route simulation and route copy costs O(n) in the worst case. Including sorting the per-vehicle alternatives, a conservative total bound is O(n^4 + vn^3 + n^2 v log(v+1)). For fixed v this is O(n^4). This implementation recomputes all options each round; it does not cache insertion evaluations between rounds. Memory is O(n^2 + vn), including the distance matrix and retained route alternatives.

## Parameters, seed, and stopping

- `regret_k`: integer >= 2, default 2; capped to the fleet size internally. Invalid values raise ValueError.
- Deterministic; the supplied seed is accepted but ignored. No restarts, local search, repair, or scenario-specific choices.
- Work unit: one attempted insertion evaluation, feasible or infeasible. Every such call spends one unit. Sorting, cached score arithmetic, empty-route initialization, and the harness's final validation are not search work units.
- `fixed_work`: check the budget before each evaluation and never exceed the candidate-evaluation target. A completed construction may stop before the target. If interrupted before completion, submit nothing; record this as no feasible plan, not an infeasibility proof.
- `time_budget`: use the same budget checks; no direct clock access. One evaluation/bookkeeping segment or final harness validation may finish after the deadline, so this is cooperative stopping, not a hard interrupt.
- The runner's existing safety limit applies. There is no uncounted fallback construction after expiry.

## Running without registry changes

From the repository root:

```bash
PYTHONPATH=src python -m ctai solve data/practice/easy_01.json \
  -a ctai.algorithms.regret_insertion:solve --mode fixed_work \
  --work-budget 20000 --show-routes

PYTHONPATH=src python -m ctai run data/practice \
  -a ctai.algorithms.regret_insertion:solve --mode time_budget \
  --time-limit 30 --seeds 1-5 --out results/regret_insertion
```

The existing dotted-path loader records the function name (`solve`) as algorithm_id. Use a dedicated output directory so records cannot collide with other unregistered algorithms. The project owner should register this module's `ALGORITHM_ID`, `ALGORITHM_NAME`, and `solve` before formal combined experiments. Registry, runner, tests, and shared configuration are intentionally unchanged under the contribution policy.

The existing CLI has no custom-k option. For k=3 through the Python interface:

```python
from ctai.algorithms.regret_insertion import solve
from ctai.budget import Budget
from ctai.instance import load_instance
from ctai.submitter import SolutionSubmitter

instance = load_instance('data/practice/easy_01.json')
submitter = SolutionSubmitter(instance)
budget = Budget(mode='fixed_work', work_budget=20000)
solve(instance, 1, {'budget': budget, 'regret_k': 3}, submitter)
print(submitter.best_score)
```

## Validation and limitations

Both k=2 and k=3 produced feasible plans on all six public practice scenarios, using 2,170 insertion evaluations per completed construction (20 customers, 4 vehicles). Default k=2 makespans in minutes: easy_01 97.33, easy_02 90.69, medium_01 97.62, medium_02 93.64, hard_01 99.33, hard_02 106.96. These are development checks, not formal experiment results or optimality claims.

This is insertion-only construction: early decisions are never undone. It can fail on a feasible instance if its partial plan leaves a customer without a feasible insertion. A tight budget can also prevent any complete submission. It need not outperform local search or simulated annealing. Full rescanning becomes expensive as n grows. Algorithm-specific work counts are not equivalent to other algorithms' counts; report actual work, completion status, elapsed time, feasibility, and objective under the approved experiment workflow.
