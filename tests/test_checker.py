"""用练习场景 example_001 自测检查器（规则文档第四节计算核对）。

预期：路线 [0,1,2,0] 合法，makespan = 34 分钟，总距离 = 12 公里。

运行：python -m tests.test_checker
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
        self.assertTrue(any("漏送" in e for e in res["validation_errors"]))

    def test_overload_is_infeasible(self):
        inst = dict(self.inst)
        inst["vehicle_capacity_kg"] = 49  # 20+30=50 > 49
        res = evaluate_routes(inst,
                              [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("超载" in e for e in res["validation_errors"]))

    def test_time_window_violation(self):
        inst = dict(self.inst)
        inst["customers"] = [
            dict(self.inst["customers"][0], time_window_min=[0, 0]),
            self.inst["customers"][1],
        ]  # 客户 1 必须在第 6 分钟到达后立刻开始服务，但 b=0
        res = evaluate_routes(inst,
                              [{"vehicle_id": 1, "stops": [0, 1, 2, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("时间窗" in e for e in res["validation_errors"]))

    def test_route_must_start_and_end_at_depot(self):
        res = evaluate_routes(self.inst,
                              [{"vehicle_id": 1, "stops": [1, 2, 0]}])
        self.assertFalse(res["feasible"])
        self.assertTrue(any("仓库" in e for e in res["validation_errors"]))


if __name__ == "__main__":
    unittest.main()
