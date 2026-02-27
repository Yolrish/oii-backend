"""
Workflow HTTP API 路由
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from .deps import get_workflow_service
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
from ..services import WorkflowService
from ..models import (
    Workflow,
    Step,
    Task,
    TaskResultContent,
    WorkflowResult,
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _task_result_content_to_schema(r: TaskResultContent | None) -> TaskResultContentSchema | None:
    if r is None:
        return None
    return TaskResultContentSchema(type=r.type, content=r.content or "")


def _task_to_response(t: Task) -> TaskResponse:
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
        result=_task_result_content_to_schema(t.result),
    )


def _step_to_response(s: Step) -> StepResponse:
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
        tasks=[_task_to_response(t) for t in s.tasks],
        on_before_path=s.on_before_path or "",
        on_start_path=s.on_start_path or "",
        on_done_path=s.on_done_path or "",
        on_retry_path=s.on_retry_path or "",
    )


def _workflow_to_response(w: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=w.id,
        name=w.name,
        description=w.description or "",
        creator=w.creator or "",
        created_at=w.created_at,
        first_step_id=w.first_step_id or "",
        end_step_id=w.end_step_id or "",
        steps=[_step_to_response(s) for s in w.steps],
        task_results={
            k: _task_result_content_to_schema(v) or TaskResultContentSchema()
            for k, v in (w.task_results or {}).items()
        },
    )


def _workflow_run_to_response(wr: WorkflowResult) -> WorkflowRunResponse:
    step_results = [
        StepResultSchema(
            step_id=sr.step_id,
            success=sr.success,
            task_results=[
                TaskResultSchema(
                    task_id=tr.task_id,
                    success=tr.success,
                    data=_task_result_content_to_schema(tr.data) if tr.data else None,
                    error=tr.error,
                )
                for tr in sr.task_results
            ],
            error=sr.error,
        )
        for sr in wr.step_results
    ]
    return WorkflowRunResponse(
        workflow_id=wr.workflow_id,
        success=wr.success,
        step_results=step_results,
        error=wr.error,
    )


# ---------- Workflow ----------


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Create a new workflow (with Start and End steps)."""
    w = await service.create_workflow(
        name=body.name,
        creator=body.creator,
        description=body.description,
    )
    return _workflow_to_response(w)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Get workflow by id (loads from DB if not in cache)."""
    w = await service.get_workflow(workflow_id)
    if not w:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return _workflow_to_response(w)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete workflow and cascade delete steps and tasks."""
    ok = await service.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return None


# ---------- Step ----------


@router.post("/{workflow_id}/steps", response_model=StepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(
    workflow_id: str,
    body: StepCreate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Add a process step before the End step."""
    step = await service.add_step(
        workflow_id,
        name=body.name,
        description=body.description,
        creator=body.creator,
        on_before_path=body.on_before_path,
        on_start_path=body.on_start_path,
        on_done_path=body.on_done_path,
        on_retry_path=body.on_retry_path,
    )
    if not step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add step (workflow not found or no end step)",
        )
    return _step_to_response(step)


@router.post(
    "/{workflow_id}/steps/after/{after_step_id}",
    response_model=StepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_step_after(
    workflow_id: str,
    after_step_id: str,
    body: StepCreate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Insert a process step after the given step (not allowed after End step)."""
    step = await service.add_step_after(
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
    if not step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add step after (workflow/step not found or cannot insert after End step)",
        )
    return _step_to_response(step)


@router.delete("/{workflow_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    workflow_id: str,
    step_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete a process step (Start and End steps cannot be deleted)."""
    ok = await service.delete_step(workflow_id, step_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Step not found or cannot delete (Start/End steps are protected)",
        )
    return None


# ---------- Task ----------


@router.post(
    "/{workflow_id}/steps/{step_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_task(
    workflow_id: str,
    step_id: str,
    body: TaskCreate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Add a task to a process step (Start/End steps cannot have tasks)."""
    task = await service.add_task(
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
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add task (workflow/step not found or step is Start/End)",
        )
    return _task_to_response(task)


@router.delete(
    "/{workflow_id}/steps/{step_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    workflow_id: str,
    step_id: str,
    task_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete a task from a step."""
    ok = await service.delete_task(workflow_id, step_id, task_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or cannot delete",
        )
    return None


# ---------- Run ----------


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: str,
    body: RunWorkflowRequest | None = None,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Run workflow: execute steps in order, tasks in parallel within each step."""
    context: Dict[str, Any] = (body and body.context) or {}
    wr = await service.run_workflow(workflow_id, context=context)
    if not wr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return _workflow_run_to_response(wr)
