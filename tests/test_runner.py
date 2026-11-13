"""The runner must measure correctly, respect both stopping rules, and survive bad submissions."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ctai.runner import RunSpec, run_once

PRACTICE = Path(__file__).resolve().parents[1] / "data" / "practice"


def boom(instance, seed, run_config, submit_solution):
    raise RuntimeError("deliberate failure")


def cheat(instance, seed, run_config, submit_solution):
    """Always submits the same illegal plan (a customer is missing)."""
    submit_solution.submit([{"vehicle_id": 1, "stops": [0, 0]}])


class TestTimeBudget(unittest.TestCase):
    def test_run_is_feasible_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = RunSpec(
                instance_path=PRACTICE / "easy_01.json",
                algorithm="greedy_insertion",
                mode="time_budget",
                time_limit_sec=0.5,
                out_dir=Path(tmp),
            )
            record = run_once(spec)

            self.assertTrue(record["feasible"])
            self.assertIn(record["termination"], {"completed", "time_budget"})
            self.assertLessEqual(record["runtime_sec"], 2.0)
            self.assertEqual(record["scenario_id"], "easy_01")

            written = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(written), 1)
            with written[0].open(encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["algorithm_id"], "greedy_insertion")


class TestFixedWork(unittest.TestCase):
    def test_work_budget_stops_the_run(self) -> None:
        spec = RunSpec(
            instance_path=PRACTICE / "medium_01.json",
            algorithm="local_search",
            mode="fixed_work",
            work_budget=2000,
            out_dir=None,
        )
        record = run_once(spec)
        self.assertTrue(record["feasible"])
        self.assertEqual(record["termination"], "work_budget")
        # the descent stops as soon as the budget is reached; one candidate may overshoot
        self.assertLessEqual(record["work_done"], 2000 + 10)

    def test_fixed_work_requires_a_budget(self) -> None:
        with self.assertRaises(ValueError):
            RunSpec(instance_path=PRACTICE / "easy_01.json", mode="fixed_work", out_dir=None)


class TestFailureHandling(unittest.TestCase):
    def test_exception_is_recorded_not_raised(self) -> None:
        spec = RunSpec(
            instance_path=PRACTICE / "easy_01.json",
            algorithm="does_not_matter",
            mode="time_budget",
            time_limit_sec=0.2,
            out_dir=None,
        )
        with mock.patch("ctai.runner.experiment.get_solver", return_value=("boom", boom)):
            record = run_once(spec)

        self.assertEqual(record["termination"], "error")
        self.assertIn("deliberate failure", record["error"])
        self.assertFalse(record["feasible"])

    def test_submitting_only_infeasible_plans_is_reported(self) -> None:
        spec = RunSpec(
            instance_path=PRACTICE / "easy_01.json",
            algorithm="does_not_matter",
            mode="time_budget",
            time_limit_sec=0.2,
            out_dir=None,
        )
        with mock.patch("ctai.runner.experiment.get_solver", return_value=("cheat", cheat)):
            record = run_once(spec)

        self.assertFalse(record["feasible"])
        self.assertIsNone(record["makespan_min"])
        self.assertGreater(record["rejections"], 0)


class TestUnknownAlgorithm(unittest.TestCase):
    def test_unknown_name_raises(self) -> None:
        spec = RunSpec(
            instance_path=PRACTICE / "easy_01.json",
            algorithm="not_registered",
            mode="time_budget",
            time_limit_sec=0.1,
            out_dir=None,
        )
        with self.assertRaises(KeyError):
            run_once(spec)


if __name__ == "__main__":
    unittest.main()
