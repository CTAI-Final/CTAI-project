"""Reporting layer: statistics over run records, and optional figures."""

from __future__ import annotations

from .statistics import load_results, summarise, to_csv, to_markdown

__all__ = ["load_results", "summarise", "to_csv", "to_markdown"]
