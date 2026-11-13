"""The practice set must be reproducible, valid and actually solvable."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ctai.budget import Budget
from ctai.datagen import PRACTICE_SPECS, generate, write_practice_set
from ctai.instance import validate_instance
from ctai.problem import Problem

PRACTICE = Path(__file__).resolve().parents[1] / "data" / "practice"


class TestGenerator(unittest.TestCase):
    def test_same_seed_gives_the_same_scenario(self) -> None:
        first = generate("demo", 20, 4, "medium", 42)
        second = generate("demo", 20, 4, "medium", 42)
        self.assertEqual(first, second)

    def test_different_seeds_differ(self) -> None:
        first = generate("demo", 20, 4, "medium", 42)
        second = generate("demo", 20, 4, "medium", 43)
        self.assertNotEqual(first["customers"], second["customers"])

    def test_generated_scenario_is_valid(self) -> None:
        for difficulty in ("easy", "medium", "hard"):
            with self.subTest(difficulty=difficulty):
                instance = generate(f"check_{difficulty}", 20, 4, difficulty, 7)
                self.assertEqual(validate_instance(instance), [])

    def test_generated_scenario_has_a_feasible_plan(self) -> None:
        """The planted solution guarantees feasibility; the constructor must find one."""
        from ctai.algorithms.base import construct

        for difficulty in ("easy", "medium", "hard"):
            with self.subTest(difficulty=difficulty):
                instance = generate(f"check_{difficulty}", 20, 4, difficulty, 7)
                plan = construct(Problem(instance), Budget(mode="fixed_work", work_budget=10**6))
                self.assertTrue(plan.feasible)

    def test_scale_sizes_are_generatable(self) -> None:
        for customers, vehicles in ((10, 2), (20, 4), (40, 8)):
            with self.subTest(customers=customers):
                instance = generate(f"scale_{customers}", customers, vehicles, "medium", 11)
                self.assertEqual(instance["customer_count"], customers)
                self.assertEqual(validate_instance(instance), [])

    def test_unknown_difficulty_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            generate("x", 10, 2, "impossible", 1)

    def test_write_practice_set_produces_six_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            written = write_practice_set(tmp)
            names = sorted(p.name for p in written)
            self.assertEqual(len(names), 7)  # six scenarios + manifest
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["scenarios"]), 6)
            for entry in manifest["scenarios"]:
                self.assertIsNotNone(entry["reference_makespan_min"])


class TestCommittedPracticeSet(unittest.TestCase):
    def test_every_committed_file_is_valid(self) -> None:
        for path in sorted(PRACTICE.glob("*.json")):
            if path.name == "manifest.json":
                continue
            with self.subTest(scenario=path.stem):
                instance = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_instance(instance), [])
                self.assertEqual(instance["customer_count"], 20)
                self.assertEqual(instance["vehicle_count"], 4)

    def test_manifest_matches_the_files(self) -> None:
        manifest = json.loads((PRACTICE / "manifest.json").read_text(encoding="utf-8"))
        listed = {entry["file"] for entry in manifest["scenarios"]}
        present = {p.name for p in PRACTICE.glob("*.json")} - {"manifest.json"}
        self.assertEqual(listed, present)

    def test_manifest_covers_the_three_difficulties(self) -> None:
        manifest = json.loads((PRACTICE / "manifest.json").read_text(encoding="utf-8"))
        difficulties = sorted({entry["difficulty"] for entry in manifest["scenarios"]})
        self.assertEqual(difficulties, ["easy", "hard", "medium"])

    def test_spec_table_matches_the_committed_files(self) -> None:
        ids = {spec[0] for spec in PRACTICE_SPECS}
        present = {p.stem for p in PRACTICE.glob("*.json")} - {"manifest"}
        self.assertEqual(ids, present)


if __name__ == "__main__":
    unittest.main()
