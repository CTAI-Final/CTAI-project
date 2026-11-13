# solver_b — Algorithm 2 (owner: TBD)

> Status: placeholder. The owner updates this README and `solver.py` once the algorithm is chosen.
> Each of the three implementers must select a **different** algorithm and report it
> (Section 1 of the rules).
>
> 中文版见 [README_zh.md](README_zh.md)。

## Candidate methods (Section 12 of the rules; options only)

- Feasible-insertion greedy with local search (relocation / exchange / intra-route reordering)
- Multi-start randomized greedy
- Simulated annealing
- Tabu search
- Genetic algorithm
- Small-scale exact search (enumeration / branch and bound, small instances only)

## Required README contents (Section 13 of the rules)

- [ ] Algorithm idea
- [ ] Reason for the choice
- [ ] Pseudocode
- [ ] Theoretical complexity (define n, k, I, ... and give the combined expression)
- [ ] Parameter table (values and tuning rationale)
- [ ] Random-seed handling (derive randomness from `seed` only; explain for deterministic algorithms)
- [ ] Limitations
- [ ] Dependencies and how to run
- [ ] `time_budget` mode: stopping strategy within 30 s (how the best feasible solution is kept)
- [ ] `fixed_work` mode: work unit, target amount, initialization and retry caps,
      actual work counting, and safety-stop behaviour

## How to run (example)

```bash
# Performance mode: 30 s budget
python -m runner.run_experiments --solver algorithms.solver_b.solver:solve \
    --instance data/practice/example_001.json --algorithm-id solver_b --seed 1 --run-index 1

# Scale mode: fixed work
python -m runner.run_experiments --solver algorithms.solver_b.solver:solve \
    --instance data/practice/example_001.json --algorithm-id solver_b --seed 1 --run-index 1 \
    --mode fixed_work --work-budget 100 --safety-limit-sec 300 --out-dir results/scale
```
