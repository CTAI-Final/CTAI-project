"""保护上限与运行状态记录（规则文档第五、八节）。

- 规模组可另设保护上限（具体秒数待审核，不默认沿用 30 秒）；
- 触及保护上限或在规定工作完成前异常退出：标记为未完成，
  保存实际工作量和已耗时间；
- 不得把保护上限时间作为完整运行时间；
- termination 取值：completed / timeout / error / safety_timeout。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunStatus:
    """单次运行状态。"""

    termination: str = "completed"       # completed/timeout/error/safety_timeout
    work_done: int | None = None         # 实际完成工作量
    work_budget: int | None = None       # 目标工作量
    safety_limit_sec: float | None = None
    error_message: str | None = None

    @property
    def work_completed(self) -> bool:
        """是否完整执行规定工作量（与是否有合法路线互相独立）。"""
        return (self.termination == "completed"
                and self.work_done is not None
                and self.work_budget is not None
                and self.work_done >= self.work_budget)

    def hit_safety_limit(self, elapsed_sec: float) -> bool:
        if self.safety_limit_sec is None:
            return False
        return elapsed_sec >= self.safety_limit_sec


def mark_safety_timeout(status: RunStatus, meter_total: int) -> RunStatus:
    status.termination = "safety_timeout"
    status.work_done = meter_total
    return status


def mark_error(status: RunStatus, exc: Exception, meter_total: int) -> RunStatus:
    status.termination = "error"
    status.work_done = meter_total
    status.error_message = f"{type(exc).__name__}: {exc}"
    return status
