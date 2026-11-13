"""工作量计数（规则文档第五节规模实验）。

规模模式固定的是**迭代等控制量**，不是底层运算次数；每步成本可以随客户数增长。
不同算法的工作单位不同（见 algorithms/<solver>/README.md），本模块只提供统一计数口径：

- 构造次数（贪心一次完整构造 = 1）
- 邻域尝试次数（模拟退火 / 禁忌搜索）
- 代数（遗传算法）
- 重启、修复和初始解构造次数（须有明确计数或重试上限，不能无限补做）
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkMeter:
    """规模模式工作量计数器。字段随算法定义，此处为建议口径。"""

    constructions: int = 0        # 完整构造次数
    neighbor_moves: int = 0       # 邻域尝试次数
    generations: int = 0          # 遗传算法代数
    restarts: int = 0             # 重启次数
    repairs: int = 0              # 修复次数
    extra: dict = field(default_factory=dict)  # 算法自定义计数

    def total(self, unit: str) -> int:
        """按声明的工作单位返回累计量。"""
        table = {
            "constructions": self.constructions,
            "neighbor_moves": self.neighbor_moves,
            "generations": self.generations,
            "restarts": self.restarts,
            "repairs": self.repairs,
        }
        if unit in table:
            return table[unit]
        return int(self.extra.get(unit, 0))

    def to_dict(self) -> dict:
        d = {
            "constructions": self.constructions,
            "neighbor_moves": self.neighbor_moves,
            "generations": self.generations,
            "restarts": self.restarts,
            "repairs": self.repairs,
        }
        d.update(self.extra)
        return d
