# Changelog

All notable changes to this repository. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — 2026-11-13

First complete scaffold, English only.

### Added

- `ctai` package with a five-layer split: geometry/instance, problem/checker/submitter, budget,
  algorithms, runner, evaluation.
- Checker covering all rules of Sections 3, 4 and 8: depot return, exact coverage, vehicle count,
  capacity, time windows, makespan and distance.
- Two stopping rules behind one object: 30 s wall clock and a machine-independent work budget,
  plus a hard safety ceiling that aborts runaway runs.
- Three reference algorithms sharing one constructor: cheapest insertion, local search over
  relocate/swap/2-opt, and simulated annealing with reheating.
- Deterministic scenario generator with a planted feasible solution; six public practice
  scenarios and a manifest recording their seeds and reference makespans.
- Runner writing one JSON record per run, including the measured plan, so any number can be
  re-verified offline.
- Statistics and optional matplotlib figures; Markdown and CSV summary output.
- CLI: `check`, `solve`, `run`, `evaluate`, `data`, `demo`.
- 43 unit tests, GitHub Actions CI on Python 3.10 / 3.12 / 3.13, MIT licence.

### Notes

- Rules remain v0.2. The open points of Section 15 are tracked as issues.
- Formal scenarios are withheld until the algorithm code is frozen.
