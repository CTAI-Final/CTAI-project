"""solver_c placeholder implementation.

Replace this file. Requirements (rules Sections 3, 11 and 12):
- implement only the core search logic; use the common package for distance computation and
  legality checking;
- submit solutions through submitter.submit(routes) (repeatedly; the best feasible solution is
  kept);
- honour both modes of run_config: time_budget (30 s) / fixed_work (fixed amount of work);
- derive randomness from `seed` only;
- never read hidden verification routes and never hard-code by scenario id.
"""

from __future__ import annotations

from common.instance import load_instance
from common.solution import SolutionSubmitter


def solve(instance: dict, seed: int, run_config: dict,
          submit_solution: "SolutionSubmitter") -> None:
    """Placeholder: assign every customer, in id order, to vehicle 1 (end-to-end smoke test).

    TODO(owner): replace with the real algorithm (construction + improvement + fixed-work
    counting).
    """
    del seed, run_config  # ignored by the placeholder; the real implementation must use them
    n = instance["customer_count"]
    routes = [{"vehicle_id": 1, "stops": [0] + list(range(1, n + 1)) + [0]}]
    submit_solution.submit(routes)
