"""Self-test of the checker with the practice scenario example_001 (rules Section 4).

Expected: route [0, 1, 2, 0] is feasible with makespan 34 minutes and total distance 12 km.

Run: python -m unittest tests.test_checker -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from common.checker import evaluate_routes
from common.instance import load_instance

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = REPO_ROOT / "data" / "practice" / "example_001.json"


class TestChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inst = load_instance(EXAMPLE)

    def test_example_route_is_feasible(self):
        res = evaluate_routes(self.inst,
                              [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertTrue(res["feasible"], res["validation_errors"])
        self.assertAlmostEqual(res["makespan_min"], 34.0, places=6)
        self.assertAlmostEqual(res["total_distance_km"], 12.0, places=6)

    def test_missing_customer_is_infeasible(self):
        res = evaluate_routes(self.inst,
                              [{"vehicle_id": 1, "stops": [0, 1, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("missing" in e for e in res["validation_errors"]))

    def test_overload_is_infeasible(self):
        inst = dict(self.inst)
        inst["vehicle_capacity_kg"] = 49  # 20 + 30 = 50 > 49
        res = evaluate_routes(inst,
                              [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("overloaded" in e for e in res["validation_errors"]))

    def test_time_window_violation(self):
        inst = dict(self.inst)
        inst["customers"] = [
            dict(self.inst["customers"][0], time_window_min=[0, 0]),
            self.inst["customers"][1],
        ]  # customer 1 is reached at minute 6, but the window closes at b = 0
        res = evaluate_routes(inst,
                              [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("time-window" in e for e in res["validation_errors"]))

    def test_route_must_start_and_end_at_depot(self):
        res = evaluate_routes(self.inst,
                              [{"vehicle_id": 1, "stops": [1, 2, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("depot" in e for e in res["validation_errors"]))


if __name__ == "__main__":
    unittest.main()
