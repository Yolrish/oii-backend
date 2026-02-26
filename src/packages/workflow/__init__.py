"""
动态 Workflow 包

支持创建 Workflow，其下多个 Step 以链的形式串行执行；每个 Step 内多个 Task 并行执行。
Step/Task 支持灵活添加、删除、编辑、重执行，并可执行外部传入的函数。
提供执行前、开始执行、执行完成、重新执行的回调接口。

使用示例：
    from packages.workflow import create_workflow_service, StepCallbacks, TaskCallbacks

    svc = create_workflow_service()
    w = svc.create_workflow("my-flow")
    step = svc.add_step(w.id, "step1", callbacks=StepCallbacks(on_before=log_before))
    svc.add_task(w.id, step.id, func=my_func, params={"key": "value"})
    result = await svc.run_workflow(w.id, context={})
"""

from .configs import WorkflowConfig, default_config
from .models import (
    StepCallbacks,
    TaskCallbacks,
    Task,
    Step,
    Workflow,
    StepResult,
    TaskResult,
    WorkflowResult,
)
from .services import (
    WorkflowService,
    create_workflow_service,
    get_default_service,
)

__all__ = [
    "WorkflowConfig",
    "default_config",
    "StepCallbacks",
    "TaskCallbacks",
    "Task",
    "Step",
    "Workflow",
    "StepResult",
    "TaskResult",
    "WorkflowResult",
    "WorkflowService",
    "create_workflow_service",
    "get_default_service",
]

__version__ = "1.0.0"
