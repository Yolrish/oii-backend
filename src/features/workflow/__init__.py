"""
动态 Workflow 包

设计：接收 AI 指定格式 → ai_spec 转为 Workflow（仅路径字符串）→ 执行时 resolve_handler 解析为函数并执行。
结构见 README「模块结构」：configs / models / services / repositories / ai_spec / api（Router + Controller util）。
"""

# 配置
from .configs import WorkflowConfig, default_config

# 领域模型与路径解析
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

# 服务层
from .services import (
    WorkflowService,
    create_workflow_service,
    get_default_service,
)

# AI 指定格式
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

# 持久化
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

# HTTP API（Router + Controller util + Schemas）
from .api import (
    router as workflow_router,
    get_workflow_service,
    WorkflowCreate,
    WorkflowResponse,
    StepCreate,
    StepUpdate,
    StepResponse,
    StepResultSchema,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskResultContentSchema,
    RunWorkflowRequest,
    WorkflowRunResponse,
    TaskResultSchema,
)

__all__ = [
    # configs
    "WorkflowConfig",
    "default_config",
    # models
    "Task",
    "TaskResultContent",
    "TaskResultType",
    "Step",
    "Workflow",
    "StepResult",
    "TaskResult",
    "WorkflowResult",
    "resolve_handler",
    # services
    "WorkflowService",
    "create_workflow_service",
    "get_default_service",
    # ai_spec
    "TaskSpec",
    "StepSpec",
    "WorkflowSpec",
    "parse_ai_workflow",
    "parse_ai_workflow_from_dict",
    "workflow_to_spec",
    "workflow_spec_to_dict",
    "dict_to_workflow_spec",
    # repositories
    "save_workflow_spec",
    "save_workflow_meta",
    "load_workflow_spec",
    "load_workflow_from_db",
    "update_workflow_spec",
    "delete_workflow_cascade",
    "save_workflow_task_result",
    "workflow_to_doc",
    "doc_to_workflow",
    # api
    "workflow_router",
    "get_workflow_service",
    "WorkflowCreate",
    "WorkflowResponse",
    "StepCreate",
    "StepUpdate",
    "StepResponse",
    "StepResultSchema",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskResultContentSchema",
    "RunWorkflowRequest",
    "WorkflowRunResponse",
    "TaskResultSchema",
]

__version__ = "1.0.0"
