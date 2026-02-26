"""
AI 指定格式对应模块

流程：接收 AI 返回的指定格式数据 → 映射为要执行的函数列表（Workflow）→ 由上到下执行。
映射点：1. 整体函数执行（execution_handler） 2. Task 的执行函数与回调（handler + on_*）。
"""
from .schemas import TaskSpec, StepSpec, WorkflowSpec
from .mapper import (
    parse_ai_workflow,
    parse_ai_workflow_from_dict,
    workflow_to_spec,
    workflow_spec_to_dict,
    dict_to_workflow_spec,
)

__all__ = [
    "TaskSpec",
    "StepSpec",
    "WorkflowSpec",
    "parse_ai_workflow",
    "parse_ai_workflow_from_dict",
    "workflow_to_spec",
    "workflow_spec_to_dict",
    "dict_to_workflow_spec",
]
