"""Multi-vehicle delivery routing benchmark (CTAI course project, Track A).

The package is split into four layers, each with a single responsibility:

``geometry`` / ``instance``
    Raw data: Euclidean geometry and scenario loading.
``problem`` / ``checker`` / ``submitter``
    The shared evaluation core: feasibility rules, objective function, result submission.
``algorithms``
    One module per submitted algorithm. Algorithms only search; they never validate or time
    themselves.
``runner`` / ``evaluation``
    Experiment control (timing, seeds, work counting, safety ceiling) and reporting.

The public entry point is the command line interface::

    python -m ctai --help
"""

from __future__ import annotations

__version__ = "0.1.0"

#: Objective order used everywhere in the project: makespan first, distance second.
__all__ = ["__version__"]
