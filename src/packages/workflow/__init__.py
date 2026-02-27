"""
动态 Workflow 包

设计初衷：根据 AI 回答自定义创建工作流。
流程：接收 AI 返回的指定格式数据 → 由 ai_spec 模块对应为要执行的函数列表 → 由上到下执行。
两处映射：1. 整体函数执行（execution_handler） 2. Task 的执行函数/回调（handler + on_* 路径）。

使用示例：
    # 从 AI 指定格式解析并执行
    from packages.workflow import dict_to_workflow_spec, parse_ai_workflow
    spec = dict_to_workflow_spec(ai_response_json)
    w = parse_ai_workflow(spec)
    result = await svc.run_workflow(w.id, context={})

    # 持久化（三张表：workflows / workflow_steps / workflow_tasks）
    from packages.workflow import save_workflow_spec, load_workflow_from_db
    await save_workflow_spec(db, "workflows", spec)
    w = await load_workflow_from_db(db, "workflows", "workflow_steps", "workflow_tasks", workflow_id)
"""

from .configs import WorkflowConfig, default_config
from .models import (
    Task,
    TaskResultContent,
    TaskResultType,
    Step,
    Workflow,
    StepResult,
    TaskResult,
    WorkflowResult,
    resolve_handler,
)
from .services import (
    WorkflowService,
    create_workflow_service,
    get_default_service,
)
from .ai_spec import (
    TaskSpec,
    StepSpec,
    WorkflowSpec,
    parse_ai_workflow,
    parse_ai_workflow_from_dict,
    workflow_to_spec,
    workflow_spec_to_dict,
    dict_to_workflow_spec,
)
from .repositories import (
    save_workflow_spec,
    save_workflow_meta,
    load_workflow_spec,
    load_workflow_from_db,
    update_workflow_spec,
    save_workflow_task_result,
    delete_workflow_cascade,
    workflow_to_doc,
    doc_to_workflow,
)

__all__ = [
    "WorkflowConfig",
    "default_config",
    "Task",
    "TaskResultContent",
    "TaskResultType",
    "Step",
    "Workflow",
    "StepResult",
    "TaskResult",
    "WorkflowResult",
    "resolve_handler",
    "WorkflowService",
    "create_workflow_service",
    "get_default_service",
    # AI 指定格式与持久化
    "TaskSpec",
    "StepSpec",
    "WorkflowSpec",
    "parse_ai_workflow",
    "parse_ai_workflow_from_dict",
    "workflow_to_spec",
    "workflow_spec_to_dict",
    "dict_to_workflow_spec",
    "save_workflow_spec",
    "save_workflow_meta",
    "load_workflow_spec",
    "load_workflow_from_db",
    "update_workflow_spec",
    "delete_workflow_cascade",
    "save_workflow_task_result",
    "workflow_to_doc",
    "doc_to_workflow",
]

__version__ = "1.0.0"
