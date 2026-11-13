"""Every registered algorithm must produce a legal, sensible plan on every practice scenario."""

from __future__ import annotations

import unittest
from pathlib import Path

from ctai.algorithms import available, get_solver
from ctai.algorithms.base import construct, relocate, swap, two_opt
from ctai.budget import Budget
from ctai.checker import evaluate_routes
from ctai.instance import load_instance
from ctai.problem import Problem
from ctai.submitter import SolutionSubmitter

PRACTICE = Path(__file__).resolve().parents[1] / "data" / "practice"


def run_algorithm(name: str, instance: dict, mode: str = "fixed_work", budget: int | float = 20000):
    problem = Problem(instance)
    submitter = SolutionSubmitter(instance, problem)
    if mode == "fixed_work":
        limit = Budget(mode="fixed_work", work_budget=int(budget))
    else:
        limit = Budget(mode="time_budget", time_limit_sec=float(budget))
    _, solver = get_solver(name)
    solver(instance, 1, {"budget": limit, "mode": mode, "seed": 1}, submitter)
    return submitter


class TestPracticeScenarios(unittest.TestCase):
    def test_files_exist(self) -> None:
        files = sorted(p.name for p in PRACTICE.glob("*.json"))
        self.assertEqual(len(files), 7, f"expected 6 scenarios + manifest, found {files}")

    def test_every_algorithm_is_feasible_on_every_scenario(self) -> None:
        for path in sorted(PRACTICE.glob("*.json")):
            if path.name == "manifest.json":
                continue
            instance = load_instance(path)
            for algorithm in available():
                with self.subTest(scenario=path.stem, algorithm=algorithm):
                    submitter = run_algorithm(algorithm, instance)
                    self.assertIsNotNone(
                        submitter.best_routes, f"{algorithm} produced no feasible plan"
                    )
                    evaluation = evaluate_routes(instance, submitter.best_routes)
                    self.assertTrue(evaluation.feasible, evaluation.errors)
                    self.assertGreater(evaluation.makespan_min or 0, 0)

    def test_improvement_beats_pure_construction(self) -> None:
        """The two improving algorithms must not be worse than the constructor on average."""
        instance = load_instance(PRACTICE / "medium_01.json")
        greedy = run_algorithm("greedy_insertion", instance).best_score
        local = run_algorithm("local_search", instance).best_score
        anneal = run_algorithm("simulated_annealing", instance).best_score
        self.assertLessEqual(local, greedy)
        self.assertLessEqual(anneal, greedy)

    def test_seeded_runs_are_reproducible(self) -> None:
        instance = load_instance(PRACTICE / "medium_01.json")
        first = run_algorithm("simulated_annealing", instance, "fixed_work", 5000).best_score
        second = run_algorithm("simulated_annealing", instance, "fixed_work", 5000).best_score
        self.assertEqual(first, second)


class TestMoveOperators(unittest.TestCase):
    """Guard the neighbourhood operators against duplicating or losing a customer."""

    def setUp(self) -> None:
        self.instance = load_instance(PRACTICE / "easy_01.json")
        self.problem = Problem(self.instance)
        self.plan = construct(self.problem, Budget(mode="fixed_work", work_budget=10**6))
        self.assertTrue(self.plan.feasible)

    def _assert_permutation(self, plan) -> None:
        served = sorted(s for route in plan.routes for s in route[1:-1])
        self.assertEqual(served, list(range(1, self.instance["customer_count"] + 1)))

    def test_every_move_keeps_a_permutation(self) -> None:
        checked = 0
        for source in range(4):
            for position in range(1, len(self.plan.routes[source]) - 1):
                for target in range(4):
                    for insert_at in range(1, len(self.plan.routes[target])):
                        candidate = relocate(self.plan, source, position, target, insert_at)
                        if candidate is not None:
                            self._assert_permutation(candidate)
                            checked += 1
        self.assertGreater(checked, 0)

    def test_intra_route_swap_keeps_a_permutation(self) -> None:
        for index, stops in enumerate(self.plan.routes):
            for i in range(1, len(stops) - 2):
                candidate = swap(self.plan, (index, i), (index, i + 1))
                if candidate is not None:
                    self._assert_permutation(candidate)

    def test_two_opt_reverses_a_segment(self) -> None:
        index = next(i for i, r in enumerate(self.plan.routes) if len(r) > 4)
        candidate = two_opt(self.plan, index, 1, 2)
        if candidate is not None:
            self._assert_permutation(candidate)


class TestDeterminism(unittest.TestCase):
    def test_construction_is_deterministic(self) -> None:
        instance = load_instance(PRACTICE / "hard_01.json")
        problem = Problem(instance)
        first = construct(problem, Budget(mode="fixed_work", work_budget=10**6))
        second = construct(problem, Budget(mode="fixed_work", work_budget=10**6))
        self.assertEqual(first.objective(), second.objective())


if __name__ == "__main__":
    unittest.main()
