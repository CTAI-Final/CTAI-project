# Multi-Vehicle Delivery Route Optimization

## Project Rules — English Version v0.2

This project compares three self-implemented delivery-optimization algorithms. The delivery performance experiment compares feasibility and solution quality in a common environment under a 30-second budget; the scale experiment measures computation time for the same algorithm under a fixed amount of work, providing support for theoretical complexity analysis. Both groups must satisfy the same delivery business rules.

This document consolidates the confirmed rules and is released to team members after review by the project owner. Items marked “suggested detail” or “pending review” have not been individually confirmed; the candidate algorithms are options only and do not represent an allocation. The current deliverable is the rules document; it does not include an implemented test program, scenario data, or experimental results. This English version is generated after the Chinese rules are approved.

Translation note: this version is translated from the Chinese review draft v0.2 (docs/rules_zh_v0.2.md). If the two versions differ in meaning, the Chinese text prevails until both are approved.

## 1. Course Positioning and Roles

Track A of the course is adopted. The work covers problem definition, the computational model, algorithm selection and justification, complexity analysis, a Python proof of concept, experimental evaluation, limitations and improvements, and the final report. The goal is to explain the applicability and trade-offs of computational methods; production-grade software is not required.

| Role | Responsibility |
|---|---|
| Project owner and evaluation lead | Defines the rules and the JSON interface; generates the practice and formal scenarios; safeguards the feasibility-verification solution; provides the legality checker and the unified test program; runs the unified execution, statistics, and visualization. |
| Three algorithm implementers | Each selects a different algorithm and reports it; implements the core steps themselves; debugs and submits code; explains the justification, theoretical complexity, parameters, and limitations. |

NumPy, Matplotlib and similar support libraries are permitted; calling an existing optimization solver to perform the entire delivery optimization is not. Team members may propose algorithms outside the candidate list. The formal comparison focuses on algorithm quality and stability and does not reduce teamwork to a single competition ranking.

## 2. Confirmed Base Parameters

| Item | Common rule |
|---|---|
| Space and depot | 20 × 20 km square; each coordinate component lies in [0, 20]; the depot has id 0 and coordinates (10, 10). |
| Distance | Any two locations are directly reachable using Euclidean distance; there are no roads, obstacles, or traffic congestion. |
| Vehicles | Homogeneous vehicles, each with a load limit of 100 kg and a fixed speed of 0.5 km per minute. |
| Departure | All vehicles performing tasks depart at time 0 with the goods already loaded; initial loading time is not counted. |
| Service | A fixed service time of 5 minutes per customer; goods weight and time window are given per customer. |
| Time units | Delivery times and durations are in minutes; algorithm computation time is in seconds. |

## 3. Mandatory Delivery Constraints

- Each customer must be served exactly once; all goods must be delivered by the same vehicle in a single trip, and splitting a delivery is not allowed.
- A vehicle may serve several customers but may make only one round; it carries all assigned goods when it departs, and the total loaded weight must not exceed 100 kg.
- Returning to the depot to reload mid-route is not allowed. A route must end back at the depot, and the vehicle does not depart again afterwards.
- The vehicle count is a maximum available count; vehicles may be left idle. Idle vehicles contribute neither travel distance nor delivery time.
- The time window [a, b] is a closed interval of permitted service start times. If the vehicle arrives early it must wait until a; service must not start later than b. Service may finish after b.
- Every formal scenario guarantees at least one feasible solution. Failure of an algorithm to find a feasible solution does not mean the scenario is infeasible.
- Global optimality is not required. A retained verification route from the project owner only proves feasibility and does not automatically constitute an optimal reference answer.

## 4. Objective and Computation Conventions

The primary objective is to minimize the completion time of all tasks, that is, the time from the common start at 0 until the last vehicle performing deliveries returns to the depot. It is neither the sum of the per-vehicle durations nor the algorithm’s computation time.

Solution update order: first compare the completion time of all tasks, then the total travel distance; if both are equal, keep the solution found first. No weighted composite score is used.

The distance and travel time between two locations i and j are computed as follows:

$$d(i,j)=\sqrt{(x_i-x_j)^2+(y_i-y_j)^2}$$

$$\tau(i,j)=\frac{d(i,j)}{v},\quad v=0.5\ \text{km/min}$$

Times are propagated in order along each vehicle’s route. Let j be the current location and i its predecessor, let the time window of customer j be $[a_j,\ b_j]$, and let the fixed service time be 5 minutes. Then:

$$A_j=E_i+\tau(i,j),\quad S_j=\max(A_j,\ a_j),\quad E_j=S_j+t_s$$

$$S_j\le b_j$$

The first leg departs from the depot at time 0, and the last leg includes the return to the depot.

The return time of vehicle k, the completion time of all tasks, and the total travel distance are computed as follows:

$$C_k=E_{L_k}+\tau(L_k,\ 0)$$

$$T=\max_k C_k$$

$$L=\sum_{(i,j)\in R} d(i,j)$$

where $L_k$ is the last customer served by vehicle k, and R is the set of legs on all used vehicle routes.

The checker simultaneously validates the input fields, customer ids, the vehicle count, start and end points, customer coverage, duplicate service, capacity, and time windows. If a candidate solution violates any single hard constraint, it cannot be a feasible result.

Suggested detail: use full floating-point precision internally and round only for presentation; a numerical comparison tolerance of $10^{-6}$ (in the respective unit) is suggested, and rounding each leg before accumulating is not allowed. The formal tolerance is frozen before the interface is released.

## 5. Operating and Stopping Rules for the Two Experiments

Delivery performance experiment (15 constraint-difficulty scenarios). Each solve has a limit of 30 seconds and may finish earlier. During a run the current best feasible solution is saved through the common interface; on timeout the best feasible solution saved before the deadline is used, and if there is none the run is recorded as a failure. The external test program is responsible for timing and stopping.

Scale experiment (9 scale scenarios). The 30-second limit is no longer used as the normal stopping condition. For a given algorithm, the work unit, the target amount of work, and the related parameters are fixed across all scales; the run stops when the work is complete and the actual computation time is recorded. What is fixed here is control quantities such as the iteration count, not the number of low-level operations; the cost of each step may grow with the number of customers.

Examples of work units: a greedy algorithm performs one complete construction; simulated annealing fixes the number of candidate neighborhood attempts; a genetic algorithm fixes the population size and the number of generations. Restarts, repairs, and initial-solution construction must have explicit counting or retry caps and must not be repeated indefinitely as difficulty increases. Different algorithms use different work units; the same iteration count does not mean an equal amount of computation, and the scale curves are mainly used to analyze each algorithm’s own growth.

The scale group may define a separate safety limit to prevent runaway runs; the exact number of seconds is pending review and does not default to 30 seconds. If the safety limit is reached, or the run exits abnormally before the required work is complete, the run is marked as not completed and the actual work done and the elapsed time are saved; the safety-limit time must not be used as a complete run time, and comparability must not be manufactured by lowering the target work at large scales. If an algorithm completes its construction normally but finds no feasible solution, the run may still serve as a timing sample of a completed computation, with the solving failure recorded as well.

Suggested timing boundary shared by both groups: input reading and common preprocessing are completed before timing starts; the algorithm’s own initialization, construction, search, and in-run solution-submission overhead are counted; final review, statistics, and plotting are not counted. The cost of common preprocessing such as the distance matrix must be recorded separately and explained in the theoretical analysis. The scale group should state that the curve measures the solving stage; if end-to-end time is reported, the common preprocessing cost must be added.

## 6. Scenarios and Repeated Runs

| Experiment group | Configuration | Scenarios |
|---|---|---|
| Constraint-difficulty group | 20 customers, 4 vehicles; 5 scenarios each for easy, medium, and hard; at most 30 seconds per run | 15 |
| Scale group | 10/20/40 customers with 2/4/8 vehicles, 3 scenarios each, medium constraints; timed with a fixed amount of work per algorithm | 9 |
| Public practice group | 2 scenarios each for easy, medium, and hard; different from the formal data | 6 (not in formal statistics) |

Formal testing uses 24 scenarios in total; each algorithm runs each scenario 5 times, that is, 120 runs per algorithm and 360 runs across the three algorithms. The delivery performance experiment accounts for 15 × 5 × 3 = 225 runs with a solving budget of at most 6,750 seconds, that is, 112.5 minutes; the scale experiment accounts for 9 × 5 × 3 = 135 runs, whose duration depends on the time needed to complete the required work. The overall experiment limit therefore cannot be stated as 180 minutes; the total must additionally include the scale experiment and the overhead of startup, validation, and output.

When a scenario is repeated, the customer and vehicle data stay exactly the same and only the algorithm’s random seed changes. Using [1, 2, 3, 4, 5] uniformly is suggested; this specific list is pending review. Algorithms must control the source of randomness they use; deterministic algorithms are also run 5 times so that timing variation can be observed.

All formal tests run serially on the same computer with the same Python and dependency environment. The environment, code commit version, seeds, and run status are recorded to avoid resource contention affecting timing.

## 7. Scenario Difficulty Generation and Confidentiality

The load factor $\rho$ is defined as the ratio of the total customer goods weight to the total available fleet capacity:

$$\rho=\frac{\sum_{i=1}^{n} w_i}{K\cdot Q}$$

where $w_i$ is the goods weight of customer i, n is the number of customers, K is the number of available vehicles, and Q = 100 kg is the per-vehicle load limit. Difficulty is adjusted through the load factor, the time-window slack, and spatial and temporal conflict. The customer count and vehicle count stay unchanged across the original 15 scenarios.

| Factor | Medium-difficulty design direction | High-difficulty design direction |
|---|---|---|
| Load factor | A certain capacity margin is retained | Capacity close to fully used, with a small allocation margin |
| Time-window slack | Wide slack is kept around the service times of a known feasible route | Smaller slack is kept around the service times |
| Spatial and temporal conflict | A few distant customers share overlapping time windows | Several groups of distant customers share overlapping time windows |

The previously discussed load factors of 70%–80% (medium) and 90%–95% (hard), together with the ±20 and ±5 minute time-window slack, are candidate examples only and have not been confirmed as generation parameters. The specific range for easy scenarios is likewise pending calibration.

Generation method: first construct vehicle assignments and routes, set customer weights that satisfy capacity, compute the service times, then construct time windows that contain those times; retain at least one complete feasible route. Re-validate after any adjustment; checking total capacity alone is not sufficient.

Calibrate the levels with a common baseline method and record the calibration evidence. Difficulty is not an absolute ranking of all algorithms, and data are not chosen after the fact according to which of the three implementers won. When several factors change at the same time, performance differences are not attributed to a single factor. The scale group keeps the medium constraint tightness as close as possible, with the vehicle count increased proportionally.

The project owner publishes the rules, scale, difficulty ranges, and the 6 practice scenarios in advance. The 24 formal scenarios and the project owner’s verification routes must not be committed to the shared repository before the deadline; after the algorithm code is frozen, the project owner uses them for unified testing. Feasibility is guaranteed and the corresponding answers are not published.

## 8. Evaluation Metrics and Statistical Rules

| Metric | Definition and statistical convention |
|---|---|
| Solution feasibility | Determined by the common checker; missed customers, duplicates, overloading, and time-window violations are all infeasible. |
| Completion time of all tasks | Mean over the feasible solutions among the 5 runs per scenario; the primary quality metric, smaller is better. |
| Total travel distance | Mean over the feasible solutions; route visualization uses the actual distance of that particular run. |
| Algorithm runtime | Performance group: mean solving time over all 5 runs, including failures, with timeouts recorded at the budget. Scale group: mean time and variation for fully executing the required work, with truncated records listed separately and not mixed with the performance group. |
| Feasible-solution success rate | Feasible runs / 5. When grouped, report feasible runs / all runs in that group. |
| Completion-time variation | Standard deviation of the completion times of feasible solutions; when fewer than 2 feasible runs exist, display “insufficient to assess variation”. |

The delivery quality statistics in this section mainly apply to the 15 performance scenarios. Timing statistics for the scale group are filtered by whether the required work was fully executed, not by whether a route is feasible: report the mean time and variation of the fully executed records, together with the full-completion rate and the number of truncated and abnormal runs; records that complete the work but find no feasible route are still counted in the timing. If some runs are truncated, the mean represents only the completed subset, and this bias must be stated; unconditional efficiency ranking is not performed.

Suggested detail: use the sample standard deviation with denominator $m-1$, where m is the number of feasible runs; this statistical detail is pending review. Failures are not recorded as 0 minutes; when all runs fail, the completion time, distance, and variation have no feasible result, and the JSON uses null rather than NaN or Infinity.

All 5 records are kept for each scenario. The route shown is the feasible solution with the smallest T, breaking ties by L and then by order of occurrence. It is called “the best solution among the five runs” and must not be called the global optimum.

The delivery performance group is summarized by easy, medium, and hard; the scale group is summarized by 10, 20, and 40 customers, mainly showing the computation time and its variation for completing a fixed amount of work. Times from the two stopping rules are not mixed, and completion times from different scales are not merged into an overall mean. Solution quality may be reported as an auxiliary result for the scale group but must be reported together with the feasibility rate.

Suggested comparison detail: first report each algorithm’s overall success rate; quality comparisons preferentially use the common scenarios in which every algorithm succeeded at least once, stating the number of common scenarios, averaging the feasible runs per scenario first and then aggregating with equal weights. Differing success counts must still be noted; scenarios in which only one algorithm succeeded are listed separately and not silently dropped. When there is no common successful scenario, no direct quality ranking is formed.

A shorter failed run is not interpreted as higher efficiency, and results are not reported as an “optimality gap” when the optimum is unknown. Measured differences relative to other algorithms may be reported, but the comparison basis must be stated.

## 9. Visualization Requirements

Produced uniformly by the project owner. For the performance group: a per-scenario metric table, a success-rate chart, a completion-time-and-variation chart, and a distance comparison chart. For the scale group: a chart of the computation time for a fixed amount of work against the number of customers, together with its variation, stating the vehicle counts, the work setting, the number of full completions, and the number of truncations. Records terminated by the safety limit are marked separately and are not used as full-time points when fitting a growth trend.

Route plots show the depot and the customer coordinates, distinguish vehicles by color, and label customer ids and visiting order; they display the algorithm, scenario, seed, completion time, total distance, and legality. An average metric does not correspond to a real route, so an average time must not be annotated on the best-route plot.

## 10. Complexity Analysis Requirements

Each implementer must derive the complexity theoretically from the actual code: define the variables actually used, such as the customer count n, the vehicle count k, the iteration count I, and the population size P; analyze initialization, construction, neighborhood generation, feasibility checking, and the iteration count; and combine them into an overall expression. Submit the variable definitions, the execution counts of the core steps, the per-step cost, the overall complexity, and an explanation against the experiments; citing only the complexity associated with an algorithm’s name is not sufficient.

The scale experiment mainly observes the growth of computation time for the same algorithm under a fixed amount of work and provides empirical support for the theoretical analysis; the three scales 10, 20, and 40 alone cannot prove a particular asymptotic complexity. In this project k grows together with n, so the report must state that the observation is made under the configuration $k=n/5$; fix parameters such as I and P and explain the role of each in the theory. A 30-second truncation does not mean that the algorithm’s complexity is O(1). The performance experiment explains the trade-off between the time budget and search quality, and the scale experiment explains the work definition and the time trend.

## 11. JSON Input and Output Specification

UTF-8 JSON is used. The field structure below is a draft interface for review; the business rules are confirmed, and the field names, error codes, and version number should be frozen before implementation. The customer count must match the array length. The depot id is fixed at 0 and customer ids are suggested to run from 1 to n; demand must be positive and not greater than 100, and the time window satisfies $0\le a\le b$ (see docs/interface_spec.md for details).

| Input field | Meaning |
|---|---|
| schema_version / scenario_id | Interface version and unique scenario id |
| depot | Depot id and coordinates x, y |
| customer_count / vehicle_count | Number of customers and maximum number of available vehicles |
| vehicle_capacity_kg / speed_km_per_min | Common load limit and speed |
| service_time_min | Common customer service time, 5 |
| customers | Array of customers, each with id, x, y, demand_kg, time_window_min |

The following is a two-customer format demonstration and is not a formal test scenario. One vehicle is used, the two customers require 50 kg in total, and the route [0, 1, 2, 0] is feasible.

```json
{
  "schema_version": "1.0", "scenario_id": "example_001",
  "depot": {"id": 0, "x": 10, "y": 10},
  "customer_count": 2, "vehicle_count": 1,
  "vehicle_capacity_kg": 100, "speed_km_per_min": 0.5,
  "service_time_min": 5,
  "customers": [
    {"id": 1, "x": 13, "y": 10, "demand_kg": 20,
     "time_window_min": [0, 30]},
    {"id": 2, "x": 13, "y": 14, "demand_kg": 30,
     "time_window_min": [0, 40]}
  ]
}
```

Calculation check: 0→1 is 3 km with 6 minutes of travel, and service ends at minute 11; 1→2 is 4 km with 8 minutes of travel, arriving at minute 19 and finishing service at minute 24; 2→0 is 5 km with 10 minutes of travel; the completion time of all tasks is 34 minutes and the total travel distance is 12 km.

It is suggested that algorithms submit only routes to the common interface and that the common test program fills in the experiment metadata, timing, and validation results; times reported by the algorithm itself are not authoritative evaluation values. One route is given per used vehicle, idle vehicles are suggested to be omitted, and the actual vehicle identifiers and structure are defined by the interface.

The output example below corresponds to the performance mode. The scale mode additionally records experiment_mode="fixed_work", work_budget, work_done, work_completed, and safety_limit_sec; the specific work configuration and its units should be defined by the configuration file and the README, and the field structure is pending interface finalization.

```json
{
  "schema_version": "1.0", "scenario_id": "example_001",
  "algorithm_id": "solver_a", "seed": 1, "run_index": 1,
  "experiment_mode": "time_budget", "time_limit_sec": 30,
  "termination": "completed", "feasible": true,
  "routes": [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}],
  "solver_runtime_sec": 0.12,
  "makespan_min": 34.0, "total_distance_km": 12.0,
  "validation_errors": []
}
```

0.12 seconds is a format example only and is not a measured result. termination is suggested to record completed, timeout, and error, with the scale group additionally distinguishing safety_timeout. feasible indicates whether a feasible route exists and work_completed indicates whether the required work was completed; the two are independent. A performance-group timeout with a feasible snapshot may count as a success; a scale-group safety timeout does not count as a complete timing sample even if a feasible route exists. Quality metrics are null when there is no feasible route.

## 12. Candidate Algorithms

The following are method-level candidates, and none is guaranteed to be best in this project. Every option must handle customer assignment, load, time windows, and the return to the depot; calling only a two-point shortest-path algorithm cannot solve the whole task. The parameters and the implementation complexity are explained by whoever selects the method.

| Candidate | Core approach and constraint handling | Implementation notes |
|---|---|---|
| Feasible-insertion greedy with local search | Insert customers one at a time into feasible positions, choosing by the increment in completion time; improve with customer relocation, exchange, or intra-route reordering, checking capacity and time windows each time. | Relatively easy to implement and suitable as a baseline; prone to local optima, and construction failure must be handled. |
| Multi-start randomized greedy | Use several random or randomized feasible construction starting points, apply local improvement to each, and keep the best feasible result. | Moderate work; easy to stop by the time budget; restart quality and diversity matter noticeably. |
| Simulated annealing | Start from a feasible solution and search with neighborhoods such as relocation and exchange; accept some worsening solutions with a temperature-based probability while always keeping the best feasible result. | Moderate work; requires an initial solution, a temperature, and a cooling rule to avoid freezing too early. |
| Tabu search | Iteratively choose a neighborhood solution and use short-term tabu records to reduce cycling back to old states; use aspiration rules to allow improvements. | Moderate to high work; the neighborhood and the tabu tenure need explanation. |
| Genetic algorithm | Maintain multiple encoded solutions and search by selection, crossover, and mutation; handle capacity and time windows by decoding, repair, or feasible construction. | Higher work; feasibility handling is the key point, and a generic permutation crossover is not enough. |
| Small-scale exact search | Enumerate or branch and bound over assignments and sequences, pruning under provable bounds. | Can serve as a small-instance check or an extra baseline; applicability to formal large instances within 30 seconds is not guaranteed. |

The suggested selection combination is: feasible-insertion greedy with local search, simulated annealing, and tabu search or a genetic algorithm. This combination is for selection only. Different methods may share distance computation, validation, and a disclosed initialization utility, but their core search logic must differ substantially.

Infeasible candidates may be explored internally, but the common save interface accepts only feasible solutions; if a penalty function is used, the penalty design must be explained, and evaluation still follows the hard constraints. All algorithms need a construction or repair strategy for a feasible initial solution and must not read hidden verification routes.

## 13. GitHub Collaboration and Submission Requirements

A single shared repository is used, and each implementer maintains an independent algorithm directory. The common interface, the practice data, the checker, and the test entry point are maintained by the project owner; formal data are kept separately until the code is frozen.

| Suggested location | Content |
|---|---|
| docs/ | Approved rules and interface specification |
| data/practice/ | The 6 public practice JSON files |
| common/ | Data loading, distance computation, legality checking, and the result-saving interface |
| algorithms/solver_a etc. | Each implementer’s code and README.md |
| runner/ | Timing, seeds, stopping control, work recording, and result output for both modes |
| evaluation/ | Statistics and visualization |
| results/ | Formal test results; the release scope is arranged by the project owner |

The README must contain the algorithm idea, the reason for the choice, pseudocode, theoretical complexity, parameters, random-seed handling, limitations, dependencies, and how to run it. It must additionally describe the time_budget and fixed_work modes separately: the 30-second stopping strategy in the former, and the work unit, target amount, initialization and retry caps, actual work counting, and safety-stop behavior in the latter. The scale-group configuration of an algorithm is frozen before formal testing. Record the Git version after submitting code, and hard-coding routes by hidden scenario id is prohibited.

The suggested interface is solve(instance, seed, run_config, submit_solution). run_config distinguishes mode="time_budget" (time_limit_sec=30) from mode="fixed_work" (work_budget and safety_limit_sec). The specific fields of the fixed work follow the algorithm definition; all experiments must no longer be controlled by the single 30-second parameter. The draft interface is released uniformly once finalized.

## 14. Implementation Order and Final Report

- Review the Chinese rules and finalize the parameters and the JSON interface; generate the English version after approval.
- Implement the common checker and the testers for both modes; verify distance, waiting, service, return to the depot, timeout snapshots, work counting, and safety truncation.
- Produce the public practice scenarios; the three implementers select their algorithms and debug.
- The project owner independently generates the formal scenarios, saves the feasibility evidence, and calibrates difficulty without publishing them in advance.
- Freeze the code, the runtime environment, and each algorithm’s fixed work setting; run 225 performance runs and 135 scale runs, 360 in total.
- Review the results, compute the grouped statistics, produce the plots, and discuss applicability and limitations in the light of the theoretical analysis.

The final report is suggested to contain, in order: problem and assumptions, model and objective, the three algorithms and the reasons for choosing them, theoretical complexity, experimental data and environment, feasibility, quality, and timing results, failure cases, limitations and improvements, division of work, and references. This document is the project execution rules and does not replace the final report, whose experiments have not yet been completed.

## 15. Remaining Details to Confirm During Review

| Item pending review | Current treatment |
|---|---|
| Difficulty parameters | Load-factor ranges, time-window widths and offsets, conflict-construction proportions, goods-weight distribution, and the specific combination of the 5 scenarios per level are not yet frozen. |
| Practice scenario scale | The count and difficulty distribution are fixed; the customer and vehicle counts are not separately determined. Covering small-scale debugging and 20-customer scenarios is suggested. |
| Random seeds and precision | Seeds [1, 2, 3, 4, 5] and a numerical tolerance of $10^{-6}$ are suggested; both are released uniformly in the end. |
| Statistical details | The sample standard deviation, the quality aggregation over common successful scenarios, and the equal-weight averaging over scenarios are suggestions in this draft and need confirmation. |
| Run anomalies | Marking anomalies as failures and keeping diagnostics is suggested; if a feasible snapshot exists before the anomaly, it is kept for analysis, but whether it counts toward the results must be confirmed uniformly. |
| Run constraints | Python and dependency versions, hardware, thread limits, and the timing boundary; each algorithm’s fixed work unit, target amount, retry cap, and the scale-group safety time limit must be frozen before the formal experiment. |
| Interface and repository | The JSON fields, the function signature, and the directories are draft suggestions; the repository is `CTAI-Final/CTAI-project` (private) and the submission deadline has not been designated yet. |

Suggested review order: first check the business rules and evaluation conventions in Sections 2 to 8, then confirm the interface and submission arrangements in Sections 11 to 13, and finally settle the remaining details in this section. Unreviewed suggestions must not be executed as confirmed requirements.

## 16. Source Documents

- Course basis: the Project_Brief.pdf provided by the user, in which Track A permits comparing several algorithms for the same problem and requires modelling, algorithm justification, complexity analysis, a Python prototype, experiments, and a discussion of limitations.
- Concept basis: the CTAI-project(1).docx provided by the user and the item-by-item confirmation record. Version v0.2 of this draft was revised, per the latest requirements, into two kinds of experiment: delivery performance comparison under a 30-second budget, and scale experiments timed with a fixed amount of work to support complexity analysis. The remaining confirmed delivery rules, scenario counts, repetition counts, and the single-machine execution arrangement are retained.
- The candidate-algorithm section is a project method suggestion, not a literature review. The final course report should be supplemented by each algorithm owner with references to the original literature or course materials for the method actually used.
