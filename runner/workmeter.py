"""Work counting (scale experiment, rules Section 5).

In scale mode what is fixed is a **control quantity such as the iteration count**, not the number
of low-level operations; the cost of each step may grow with the number of customers. Different
algorithms use different work units (see algorithms/<solver>/README.md); this module only provides
a common counting convention:

- complete constructions (one full greedy construction = 1)
- neighbourhood attempts (simulated annealing / tabu search)
- generations (genetic algorithm)
- restarts, repairs and initial-solution constructions (must have an explicit count or retry cap
  and must not be repeated indefinitely)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkMeter:
    """Scale-mode work counter. Fields follow the algorithm definition; these are suggested."""

    constructions: int = 0        # complete constructions
    neighbor_moves: int = 0       # neighbourhood attempts
    generations: int = 0          # genetic-algorithm generations
    restarts: int = 0             # restarts
    repairs: int = 0              # repairs
    extra: dict = field(default_factory=dict)  # algorithm-specific counters

    def total(self, unit: str) -> int:
        """Return the accumulated amount for the declared work unit."""
        table = {
            "constructions": self.constructions,
            "neighbor_moves": self.neighbor_moves,
            "generations": self.generations,
            "restarts": self.restarts,
            "repairs": self.repairs,
        }
        if unit in table:
            return table[unit]
        return int(self.extra.get(unit, 0))

    def to_dict(self) -> dict:
        d = {
            "constructions": self.constructions,
            "neighbor_moves": self.neighbor_moves,
            "generations": self.generations,
            "restarts": self.restarts,
            "repairs": self.repairs,
        }
        d.update(self.extra)
        return d
