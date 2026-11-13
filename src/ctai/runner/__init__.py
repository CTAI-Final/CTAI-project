"""Experiment layer: run one algorithm, run a whole matrix, write one JSON record per run."""

from __future__ import annotations

from .experiment import (
    RunSpec,
    format_record,
    result_filename,
    run_batch,
    run_once,
    write_result,
)

__all__ = [
    "RunSpec",
    "run_once",
    "run_batch",
    "format_record",
    "result_filename",
    "write_result",
]
