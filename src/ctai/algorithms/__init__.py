"""Algorithm registry.

Every submitted algorithm exposes ``solve(instance, seed, run_config, submit_solution)``. The
runner accepts either a registry key (``local_search``) or an explicit dotted path
(``my_package.my_module:solve``) so an external submission never has to be merged into this
package to be measured.

Adding an algorithm
-------------------
1. create ``src/ctai/algorithms/<name>.py`` with a module-level ``solve``;
2. register it in :data:`REGISTRY` below;
3. document it in ``docs/algorithms/<name>.md``;
4. add it to the matrix in ``.github/workflows/ci.yml``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Callable

from . import greedy_insertion, local_search, simulated_annealing

Solver = Callable[[dict, int, dict, object], None]

REGISTRY: dict[str, Solver] = {
    greedy_insertion.ALGORITHM_ID: greedy_insertion.solve,
    local_search.ALGORITHM_ID: local_search.solve,
    simulated_annealing.ALGORITHM_ID: simulated_annealing.solve,
}

DESCRIPTIONS: dict[str, str] = {
    greedy_insertion.ALGORITHM_ID: greedy_insertion.ALGORITHM_NAME,
    local_search.ALGORITHM_ID: local_search.ALGORITHM_NAME,
    simulated_annealing.ALGORITHM_ID: simulated_annealing.ALGORITHM_NAME,
}


def get_solver(spec: str) -> tuple[str, Solver]:
    """Resolve ``"name"`` or ``"package.module:function"`` to ``(algorithm_id, callable)``."""
    if ":" in spec:
        module_path, function_name = spec.split(":", 1)
        module = import_module(module_path)
        return function_name, getattr(module, function_name)
    if spec not in REGISTRY:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown algorithm '{spec}'; registered algorithms: {known}")
    return spec, REGISTRY[spec]


def available() -> list[str]:
    return sorted(REGISTRY)


__all__ = ["REGISTRY", "DESCRIPTIONS", "Solver", "get_solver", "available"]
