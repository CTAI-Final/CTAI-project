"""Unit tests for the rule-level checker (the contract every algorithm is judged by)."""

from __future__ import annotations

import unittest

from ctai.budget import Budget, SafetyLimitExceeded
from ctai.checker import evaluate_routes
from ctai.instance import validate_instance
from ctai.problem import Problem


def tiny_instance(**overrides) -> dict:
    """Two customers, one vehicle: 3 + 4 + 5 km of driving and 3 + 4 -> 12 km / 34 min."""
    instance = {
        "schema_version": "1.0",
        "scenario_id": "tiny",
        "depot": {"id": 0, "x": 10, "y": 10},
        "customer_count": 2,
        "vehicle_count": 1,
        "vehicle_capacity_kg": 100,
        "speed_km_per_min": 0.5,
        "service_time_min": 5,
        "customers": [
            {"id": 1, "x": 13, "y": 10, "demand_kg": 20, "time_window_min": [0, 30]},
            {"id": 2, "x": 13, "y": 14, "demand_kg": 30, "time_window_min": [0, 40]},
        ],
    }
    instance.update(overrides)
    return instance


class TestObjectives(unittest.TestCase):
    def test_travel_and_service_arithmetic(self) -> None:
        evaluation = evaluate_routes(tiny_instance(), [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertTrue(evaluation.feasible)
        # 3 km + 4 km + 5 km = 12 km, 24 min driving + 2 x 5 min service = 34 min
        self.assertAlmostEqual(evaluation.total_distance_km, 12.0, places=6)
        self.assertAlmostEqual(evaluation.makespan_min, 34.0, places=6)

    def test_waiting_for_an_early_window(self) -> None:
        instance = tiny_instance()
        instance["customers"][0]["time_window_min"] = [20, 30]
        evaluation = evaluate_routes(instance, [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertTrue(evaluation.feasible)
        # arrival at 6 min, service starts at 20 min -> 14 min of waiting
        self.assertAlmostEqual(evaluation.makespan_min, 34.0 + 14.0, places=6)


class TestRuleViolations(unittest.TestCase):
    def test_missing_customer_is_infeasible(self) -> None:
        evaluation = evaluate_routes(tiny_instance(), [{"vehicle_id": 1, "stops": [0, 1, 0]}])
        self.assertFalse(evaluation.feasible)
        self.assertIsNone(evaluation.makespan_min)
        self.assertTrue(any("not served" in e for e in evaluation.errors))

    def test_duplicate_customer_is_infeasible(self) -> None:
        evaluation = evaluate_routes(
            tiny_instance(), [{"vehicle_id": 1, "stops": [0, 1, 1, 2, 0]}]
        )
        self.assertFalse(evaluation.feasible)
        self.assertTrue(any("more than once" in e for e in evaluation.errors))

    def test_route_must_return_to_the_depot(self) -> None:
        evaluation = evaluate_routes(tiny_instance(), [{"vehicle_id": 1, "stops": [0, 1, 2]}])
        self.assertFalse(evaluation.feasible)
        self.assertTrue(any("depot" in e for e in evaluation.errors))

    def test_capacity_is_enforced(self) -> None:
        instance = tiny_instance()
        instance["customers"][0]["demand_kg"] = 80
        instance["customers"][1]["demand_kg"] = 80
        evaluation = evaluate_routes(instance, [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertFalse(evaluation.feasible)
        self.assertTrue(any("capacity" in e for e in evaluation.errors))

    def test_late_service_is_rejected(self) -> None:
        instance = tiny_instance()
        instance["customers"][1]["time_window_min"] = [0, 10]
        evaluation = evaluate_routes(instance, [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertFalse(evaluation.feasible)
        self.assertTrue(any("time-window" in e for e in evaluation.errors))
        # arriving early is not an error: the vehicle simply waits
        instance["customers"][1]["time_window_min"] = [25, 30]
        self.assertTrue(
            evaluate_routes(instance, [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}]).feasible
        )

    def test_unknown_vehicle_id_is_rejected(self) -> None:
        evaluation = evaluate_routes(tiny_instance(), [{"vehicle_id": 7, "stops": [0, 1, 2, 0]}])
        self.assertFalse(evaluation.feasible)

    def test_infeasible_plan_has_no_score(self) -> None:
        evaluation = evaluate_routes(tiny_instance(), [{"vehicle_id": 1, "stops": [0, 1, 0]}])
        self.assertEqual(evaluation.score, (float("inf"), float("inf")))


class TestInstanceValidation(unittest.TestCase):
    def test_valid_instance_has_no_errors(self) -> None:
        self.assertEqual(validate_instance(tiny_instance()), [])

    def test_count_mismatch_is_reported(self) -> None:
        errors = validate_instance(tiny_instance(customer_count=3))
        self.assertTrue(any("customer_count" in e for e in errors))

    def test_demand_beyond_capacity_is_reported(self) -> None:
        instance = tiny_instance()
        instance["customers"][0]["demand_kg"] = 150
        self.assertTrue(validate_instance(instance))

    def test_inverted_window_is_reported(self) -> None:
        instance = tiny_instance()
        instance["customers"][0]["time_window_min"] = [30, 10]
        self.assertTrue(validate_instance(instance))


class TestProblem(unittest.TestCase):
    def test_empty_plan_is_free(self) -> None:
        problem = Problem(tiny_instance())
        for route in problem.empty_plan():
            stats = problem.evaluate_path(route)
            self.assertEqual(stats.completion_min, 0.0)
            self.assertEqual(stats.distance_km, 0.0)
            self.assertTrue(stats.feasible)


class TestBudget(unittest.TestCase):
    def test_time_budget_expires(self) -> None:
        budget = Budget(mode="time_budget", time_limit_sec=0.0)
        self.assertTrue(budget.expired())
        self.assertEqual(budget.stop_reason(), "time_budget")

    def test_work_budget_expires(self) -> None:
        budget = Budget(mode="fixed_work", work_budget=3)
        self.assertFalse(budget.expired())
        budget.spend(3)
        self.assertTrue(budget.expired())
        self.assertEqual(budget.stop_reason(), "work_budget")

    def test_safety_ceiling_raises(self) -> None:
        budget = Budget(mode="time_budget", time_limit_sec=100, safety_limit_sec=0.0)
        with self.assertRaises(SafetyLimitExceeded):
            budget.check()

    def test_fixed_work_requires_a_budget(self) -> None:
        with self.assertRaises(ValueError):
            Budget(mode="fixed_work")


if __name__ == "__main__":
    unittest.main()
