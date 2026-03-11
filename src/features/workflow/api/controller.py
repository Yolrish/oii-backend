"""
Workflow API Controller 层（util 函数，非类）

供内部或 Router 调用的业务入口：接收 WorkflowService + 参数，返回领域模型或 None/False。
含领域模型 → 响应 Schema 的转换函数。不依赖 FastAPI。
"""
from typing import Any, Dict, Optional

from ..models import (
    Workflow,
    Step,
    Task,
    TaskResultContent,
    WorkflowResult,
    StepResult,
    TaskResult,
)
from ..services import WorkflowService
from .schemas import (
    WorkflowCreate,
    WorkflowResponse,
    StepCreate,
    StepUpdate,
    StepResponse,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskResultContentSchema,
    RunWorkflowRequest,
    WorkflowRunResponse,
    StepResultSchema,
    TaskResultSchema,
)


# ---------- 领域模型 → 响应 Schema 转换（供 Router 与内部序列化使用） ----------


def task_result_content_to_schema(
    r: TaskResultContent | None,
) -> TaskResultContentSchema | None:
    if r is None:
        return None
    return TaskResultContentSchema(type=r.type, content=r.content or "")


def task_to_response(t: Task) -> TaskResponse:
    return TaskResponse(
        id=t.id,
        name=t.name,
        description=t.description or "",
        parent_step_id=t.parent_step_id or "",
        parent_workflow_id=t.parent_workflow_id or "",
        creator=t.creator or "",
        created_at=t.created_at,
        run_status=t.run_status,
        handler_path=t.handler_path or "",
        params=t.params if isinstance(t.params, dict) else None,
        on_before_path=t.on_before_path or "",
        on_start_path=t.on_start_path or "",
        on_done_path=t.on_done_path or "",
        on_retry_path=t.on_retry_path or "",
        result=task_result_content_to_schema(t.result),
    )


def step_to_response(s: Step) -> StepResponse:
    return StepResponse(
        id=s.id,
        type=s.type,
        name=s.name,
        description=s.description or "",
        parent_workflow_id=s.parent_workflow_id or "",
        previous_step_id=s.previous_step_id or "",
        next_step_id=s.next_step_id or "",
        creator=s.creator or "",
        created_at=s.created_at,
        tasks=[task_to_response(t) for t in s.tasks],
        on_before_path=s.on_before_path or "",
        on_start_path=s.on_start_path or "",
        on_done_path=s.on_done_path or "",
        on_retry_path=s.on_retry_path or "",
    )


def workflow_to_response(w: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=w.id,
        name=w.name,
        description=w.description or "",
        creator=w.creator or "",
        created_at=w.created_at,
        first_step_id=w.first_step_id or "",
        end_step_id=w.end_step_id or "",
        steps=[step_to_response(s) for s in w.steps],
        task_results={
            k: task_result_content_to_schema(v) or TaskResultContentSchema()
            for k, v in (w.task_results or {}).items()
        },
    )


def task_result_to_schema(tr: TaskResult) -> TaskResultSchema:
    """单条 Task 执行结果 → Schema"""
    return TaskResultSchema(
        task_id=tr.task_id,
        success=tr.success,
        data=task_result_content_to_schema(tr.data) if tr.data else None,
        error=tr.error,
    )


def step_result_to_schema(sr: StepResult) -> StepResultSchema:
    """单条 Step 执行结果 → Schema"""
    return StepResultSchema(
        step_id=sr.step_id,
        success=sr.success,
        task_results=[task_result_to_schema(tr) for tr in sr.task_results],
        error=sr.error,
    )


def workflow_run_to_response(wr: WorkflowResult) -> WorkflowRunResponse:
    step_results = [step_result_to_schema(sr) for sr in wr.step_results]
    return WorkflowRunResponse(
        workflow_id=wr.workflow_id,
        success=wr.success,
        step_results=step_results,
        error=wr.error,
    )


# ---------- Workflow 业务入口（供内部或 Router 调用） ----------


async def create_workflow_from_ai(
    service: WorkflowService,
    body: Dict[str, Any],
) -> Workflow:
    """从 AI 指定格式创建并注册 Workflow。"""
    return await service.register_workflow_from_ai(body)


async def create_workflow(
    service: WorkflowService,
    body: WorkflowCreate,
) -> Workflow:
    """创建新 Workflow（含 Start/End 节点）。"""
    return await service.create_workflow(
        name=body.name,
        creator=body.creator,
        description=body.description,
    )


async def get_workflow(
    service: WorkflowService,
    workflow_id: str,
) -> Optional[Workflow]:
    """按 id 获取 Workflow，未命中则返回 None。"""
    return await service.get_workflow(workflow_id)


async def delete_workflow(
    service: WorkflowService,
    workflow_id: str,
) -> bool:
    """删除 Workflow 并级联删除 steps/tasks。成功返回 True。"""
    return await service.delete_workflow(workflow_id)


# ---------- Step 业务入口 ----------


async def add_step(
    service: WorkflowService,
    workflow_id: str,
    body: StepCreate,
) -> Optional[Step]:
    """在结束节点前添加过程 Step。失败返回 None。"""
    return await service.add_step(
        workflow_id,
        name=body.name,
        description=body.description,
        creator=body.creator,
        on_before_path=body.on_before_path,
        on_start_path=body.on_start_path,
        on_done_path=body.on_done_path,
        on_retry_path=body.on_retry_path,
    )


async def add_step_after(
    service: WorkflowService,
    workflow_id: str,
    after_step_id: str,
    body: StepCreate,
) -> Optional[Step]:
    """在指定 Step 后插入过程 Step。失败返回 None。"""
    return await service.add_step_after(
        workflow_id,
        after_step_id,
        name=body.name,
        description=body.description,
        creator=body.creator,
        on_before_path=body.on_before_path,
        on_start_path=body.on_start_path,
        on_done_path=body.on_done_path,
        on_retry_path=body.on_retry_path,
    )


async def delete_step(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
) -> bool:
    """删除过程 Step（Start/End 不可删）。成功返回 True。"""
    return await service.delete_step(workflow_id, step_id)


async def edit_step(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
    body: StepUpdate,
) -> Optional[Step]:
    """编辑 Step（名称、描述、创建者与回调路径）。失败返回 None。"""
    return await service.edit_step(
        workflow_id,
        step_id,
        name=body.name,
        description=body.description,
        creator=body.creator,
        on_before_path=body.on_before_path,
        on_start_path=body.on_start_path,
        on_done_path=body.on_done_path,
        on_retry_path=body.on_retry_path,
    )


async def re_run_step(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[StepResult]:
    """重执行指定 Step（先触发 on_retry_path）。未找到返回 None。"""
    return await service.re_run_step(workflow_id, step_id, context=context)


# ---------- Task 业务入口 ----------


async def add_task(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
    body: TaskCreate,
) -> Optional[Task]:
    """在过程 Step 上添加 Task。失败返回 None。"""
    return await service.add_task(
        workflow_id,
        step_id,
        name=body.name,
        description=body.description,
        creator=body.creator,
        handler_path=body.handler_path,
        params=body.params,
        on_before_path=body.on_before_path,
        on_start_path=body.on_start_path,
        on_done_path=body.on_done_path,
        on_retry_path=body.on_retry_path,
    )


async def delete_task(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
    task_id: str,
) -> bool:
    """删除 Step 下的 Task。成功返回 True。"""
    return await service.delete_task(workflow_id, step_id, task_id)


async def edit_task(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
    task_id: str,
    body: TaskUpdate,
) -> Optional[Task]:
    """编辑 Task（名称、描述、handler_path、params 与回调路径）。失败返回 None。"""
    return await service.edit_task(
        workflow_id,
        step_id,
        task_id,
        name=body.name,
        description=body.description,
        creator=body.creator,
        handler_path=body.handler_path,
        params=body.params,
        on_before_path=body.on_before_path,
        on_start_path=body.on_start_path,
        on_done_path=body.on_done_path,
        on_retry_path=body.on_retry_path,
    )


async def re_run_task(
    service: WorkflowService,
    workflow_id: str,
    step_id: str,
    task_id: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[TaskResult]:
    """重执行指定 Task（先触发 on_retry_path）。未找到返回 None。"""
    return await service.re_run_task(
        workflow_id, step_id, task_id, context=context
    )


# ---------- 执行 ----------


async def run_workflow(
    service: WorkflowService,
    workflow_id: str,
    body: Optional[RunWorkflowRequest] = None,
) -> Optional[WorkflowResult]:
    """执行 Workflow。未找到返回 None。"""
    context: Dict[str, Any] = (body and body.context) or {}
    return await service.run_workflow(workflow_id, context=context)


async def persist_workflow(
    service: WorkflowService,
    workflow_id: str,
) -> bool:
    """将 Workflow 全量同步到三张表。未配置持久化或未找到返回 False。"""
    return await service.persist_workflow(workflow_id)
