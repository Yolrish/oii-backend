"""
Workflow 运行配置
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkflowConfig:
    """
    工作流执行配置
    """
    # 单个 step 超时（秒），0 表示不限制
    step_timeout: float = 0.0
    # 单个 task 超时（秒），0 表示不限制
    task_timeout: float = 0.0
    # step 内 task 并发上限，0 表示不限制（全部并行）
    max_task_concurrent: int = 0


default_config = WorkflowConfig()
