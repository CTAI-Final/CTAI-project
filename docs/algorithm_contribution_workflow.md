# Algorithm Contribution and Experiment Workflow

This document records the project owner's approved workflow for adding candidate algorithms and running the unified experiments.

## Candidate algorithms and ownership

The project owner publishes the candidate list and decides which algorithms enter the formal comparison. The list is open; the three algorithms currently in the repository are reference implementations, not a limit on future choices. Each participant owns one selected algorithm.

## Submission boundary

Each participant works on a personal branch and submits one pull request containing only:

- `src/ctai/algorithms/<algorithm_id>.py`: the algorithm implementation, exposing the agreed `solve(...)` entry point.
- `docs/algorithms/<algorithm_id>.md`: the algorithm note.

Participants do not commit directly to `main` and do not modify shared code, tests, data, configuration, or the runner. The project owner reviews and merges accepted changes and handles registry or runner integration. Changes outside the two owned files must be requested separately and approved by the project owner.

The algorithm note must describe the idea, rationale, pseudocode, complexity, parameters, seed handling, limitations, dependencies, run instructions, and both stopping modes.

## Dependencies

Use the Python standard library by default. A participant who needs a third-party dependency must request approval in the pull request and explain its purpose, version, alternatives, and impact on runtime and reproducibility. After approval, the project owner adds and pins the dependency in the shared project configuration. Formal runs use one recorded environment.

## Experiments and work accounting

### Performance experiment

All selected algorithms use the same time limit and common evaluation rules. This is the primary cross-algorithm comparison.

### Scale experiment

Each algorithm defines its own work unit, counter, and target amount. The definition may reflect that algorithm's operation, such as a full construction, a neighborhood pass, or a candidate-neighbor evaluation. The same algorithm uses the same unit and target at every scale. Work-unit counts from different algorithms are not treated as equivalent.

The algorithm note must specify how initialization, restarts, repairs, and other extra work are counted or capped. These steps must not repeat without a bound or be silently reduced at larger scales. Record work completed, elapsed time, and whether the target was completed. Define a safety time limit before formal runs; a run stopped by that limit is incomplete, not a completed timing sample.

## Unified execution by the project owner

Participants validate their implementation on public practice data. The project owner reviews each pull request, runs the shared validation and integration workflow, selects the formal algorithm set, and runs the experiments serially on one recorded machine and environment. Formal scenarios are generated only after code and experiment settings are frozen.

## Freeze and changes

Before formal scenario generation, the project owner freezes the selected code revision, algorithm parameters, dependencies, seeds, work-unit definitions and targets, safety limits, and runtime environment.

After freeze, parameter changes or necessary code fixes require project-owner approval. Record the new revision and rerun the affected algorithm's complete formal experiment set. If shared checker, runner, or experiment rules change, the project owner decides which runs must be repeated. Keep results from different code or parameter versions separate; do not tune against formal outcomes.

## Submission review

The project owner checks that the pull request changes only the participant's two files, that the algorithm note is complete, that CI passes, and that the implementation can be registered and run through the shared harness. Acceptance into the formal comparison is a separate decision from merging the contribution.
