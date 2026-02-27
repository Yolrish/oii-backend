"""
AI 指定格式的 Schema（可序列化）

用于：接收 AI 返回的指定格式数据 → 对应为要执行的函数列表（handler_path + 回调 path）。
两处映射：1. 整体执行（可选 execution_handler） 2. Task 的执行函数与回调（handler + on_* 路径）。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaskSpec:
    """
    单任务的 AI 指定格式
    映射：handler → 要执行的函数；on_before/on_start/on_done/on_retry → 回调函数（均为模块路径字符串）
    """

    # 要执行的函数：模块路径，如 "myapp.actions.fetch_data"
    handler: str = ""
    # 传给该函数的参数（可序列化 dict）
    params: Dict[str, Any] = field(default_factory=dict)
    # 可选展示名
    name: str = ""
    # 回调函数路径（可选），加载时解析为 callable 注入 Task.callbacks
    on_before: str = ""
    on_start: str = ""
    on_done: str = ""
    on_retry: str = ""


@dataclass
class StepSpec:
    """
    单步骤的 AI 指定格式
    包含多个 TaskSpec（步骤内并行）；步骤间按列表顺序串行。
    """

    name: str = ""
    tasks: List[TaskSpec] = field(default_factory=list)
    # 步骤级回调路径（可选）
    on_before: str = ""
    on_start: str = ""
    on_done: str = ""
    on_retry: str = ""

    def __post_init__(self) -> None:
        if self.tasks is None:
            self.tasks = []


@dataclass
class WorkflowSpec:
    """
    工作流的 AI 指定格式（源数据，可整份落库）
    由上到下对应为：Step 串行 → 每 Step 内 Task 并行；整体可选 execution_handler。
    """

    name: str = ""
    steps: List[StepSpec] = field(default_factory=list)
    # 可选：整体执行入口的模块路径（如自定义 runner），未设则按默认「串 step + 步内并行 task」执行
    execution_handler: str = ""

    def __post_init__(self) -> None:
        if self.steps is None:
            self.steps = []
