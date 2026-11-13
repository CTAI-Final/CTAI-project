"""计时边界控制（规则文档第五节计时边界建议）。

- 输入读取及公共预处理（距离矩阵等）在计时**前**完成；
- 算法自身初始化、构造、搜索和运行中的方案提交开销**计入**；
- 最终复核、统计、绘图**不计入**；
- 预处理成本单独记录，供理论分析说明。
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Timer:
    """求解阶段计时器（秒）。"""

    elapsed: float = 0.0
    _start: float | None = None
    records: list[float] = field(default_factory=list)

    def start(self) -> None:
        self._start = time.perf_counter()

    def stop(self) -> float:
        if self._start is not None:
            seg = time.perf_counter() - self._start
            self.elapsed += seg
            self.records.append(seg)
            self._start = None
        return self.elapsed

    @property
    def running(self) -> bool:
        return self._start is not None


@contextmanager
def measure(out: dict, key: str):
    """把一段耗时可写入 out[key]（秒）。用于区分预处理/求解/复核阶段。"""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        out[key] = out.get(key, 0.0) + (time.perf_counter() - t0)


def within_budget(timer: Timer, time_limit_sec: float) -> bool:
    """性能模式：是否仍在 30 秒预算内。"""
    return timer.elapsed < time_limit_sec
