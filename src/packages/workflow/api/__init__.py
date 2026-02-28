"""
Workflow HTTP API 子包

分层：Router（Web 接口）基于 Controller（内部可调用的业务入口），Controller 基于 Service。
"""
from .controller import (
    create_workflow,
    create_workflow_from_ai,
    get_workflow,
    delete_workflow,
    add_step,
    add_step_after,
    delete_step,
    add_task,
    delete_task,
    run_workflow,
    workflow_to_response,
    step_to_response,
    task_to_response,
    workflow_run_to_response,
)
from .deps import get_workflow_service
from .routes import router
from .schemas import (
    WorkflowCreate,
    WorkflowResponse,
    StepCreate,
    StepResponse,
    TaskCreate,
    TaskResponse,
    TaskResultContentSchema,
    RunWorkflowRequest,
    WorkflowRunResponse,
    StepResultSchema,
    TaskResultSchema,
)

__all__ = [
    "router",
    "get_workflow_service",
    "create_workflow",
    "create_workflow_from_ai",
    "get_workflow",
    "delete_workflow",
    "add_step",
    "add_step_after",
    "delete_step",
    "add_task",
    "delete_task",
    "run_workflow",
    "workflow_to_response",
    "step_to_response",
    "task_to_response",
    "workflow_run_to_response",
    "WorkflowCreate",
    "WorkflowResponse",
    "StepCreate",
    "StepResponse",
    "TaskCreate",
    "TaskResponse",
    "TaskResultContentSchema",
    "RunWorkflowRequest",
    "WorkflowRunResponse",
    "StepResultSchema",
    "TaskResultSchema",
]
