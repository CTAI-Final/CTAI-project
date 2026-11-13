# Contributing

## Who owns what

| Area | Owner | Rule |
|---|---|---|
| `docs/`, `data/`, `src/ctai/*.py`, `src/ctai/runner/`, `src/ctai/evaluation/`, `tests/` | Project owner / evaluation lead | Change by pull request only |
| `src/ctai/algorithms/<yours>.py`, `docs/algorithms/<yours>.md` | The implementer of that algorithm | Change freely on your own branch |

An algorithm directory is never imported by another algorithm. If you need something from the
shared core, open a pull request against the owner instead of editing the core from your branch.

## Workflow

```bash
git switch -c algorithm/<name>
# edit your module + your note
make test
git commit -m "algorithm: <what changed>"
git push -u origin algorithm/<name>
```

Then open a pull request using the template. One algorithm per pull request; do not mix a checker
change with an algorithm change.

## Definition of done for an algorithm submission

1. `python -m ctai solve data/practice/<any>.json -a <yours>` produces a feasible plan for all
   six practice scenarios.
2. `docs/algorithms/<yours>.md` contains: idea, reason for the choice, pseudocode, complexity,
   parameters, seed handling, limitations, dependencies, how to run, and the behaviour of both
   `time_budget` and `fixed_work` modes.
3. Work is counted as defined in `docs/interface.md` (one unit = one candidate evaluation).
4. No dependency outside the Python standard library, unless approved by the project owner.
5. `make test` passes and no existing test was modified to make it pass.

## Ground rules

* Never hard-code a route, and never branch on `scenario_id`.
* Never read formal scenario data or verification routes — only `data/practice/` and the data your
  own runs produce.
* Never modify `checker.py` or `problem.py` to make a plan pass. If you believe a rule is wrong,
  raise an issue with the scenario file and the exact numbers.
* Keep the wall clock out of the algorithm: poll `budget.expired()`, never `time.time()`.

## Commit messages

`<area>: <imperative summary>` — `checker: reject duplicate vehicle ids`,
`algorithm/sa: reheat when temperature drops`, `docs: describe work units`.
