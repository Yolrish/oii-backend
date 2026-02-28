"""
Workflow HTTP API Router 层

仅负责 Web：解析请求、调用 controller 中的 util、将返回值转为响应并设置状态码。
"""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status

from .controller import (
    create_workflow as ctrl_create_workflow,
    create_workflow_from_ai as ctrl_create_workflow_from_ai,
    get_workflow as ctrl_get_workflow,
    delete_workflow as ctrl_delete_workflow,
    add_step as ctrl_add_step,
    add_step_after as ctrl_add_step_after,
    delete_step as ctrl_delete_step,
    add_task as ctrl_add_task,
    delete_task as ctrl_delete_task,
    run_workflow as ctrl_run_workflow,
    workflow_to_response,
    step_to_response,
    task_to_response,
    workflow_run_to_response,
)
from .deps import get_workflow_service
from .schemas import (
    WorkflowCreate,
    WorkflowResponse,
    StepCreate,
    StepResponse,
    TaskCreate,
    TaskResponse,
    RunWorkflowRequest,
    WorkflowRunResponse,
)
from ..services import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# ---------- Workflow ----------


@router.post(
    "/from-ai",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_from_ai(
    body: Dict[str, Any] = Body(
        ...,
        description="AI 指定格式：{ name, steps: [ { name, tasks: [ { handler, params } ] } ] }",
    ),
    service: WorkflowService = Depends(get_workflow_service),
):
    """接收 AI 返回的指定格式 JSON，解析为 Workflow 并注册；可随后 GET /{id} 或 POST /{id}/run。"""
    w = await ctrl_create_workflow_from_ai(service, body)
    return workflow_to_response(w)


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Create a new workflow (with Start and End steps)."""
    w = await ctrl_create_workflow(service, body)
    return workflow_to_response(w)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Get workflow by id (loads from DB if not in cache)."""
    w = await ctrl_get_workflow(service, workflow_id)
    if not w:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return workflow_to_response(w)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete workflow and cascade delete steps and tasks."""
    ok = await ctrl_delete_workflow(service, workflow_id)
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
    step = await ctrl_add_step(service, workflow_id, body)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add step (workflow not found or no end step)",
        )
    return step_to_response(step)


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
    step = await ctrl_add_step_after(service, workflow_id, after_step_id, body)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add step after (workflow/step not found or cannot insert after End step)",
        )
    return step_to_response(step)


@router.delete("/{workflow_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    workflow_id: str,
    step_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete a process step (Start and End steps cannot be deleted)."""
    ok = await ctrl_delete_step(service, workflow_id, step_id)
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
    task = await ctrl_add_task(service, workflow_id, step_id, body)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add task (workflow/step not found or step is Start/End)",
        )
    return task_to_response(task)


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
    ok = await ctrl_delete_task(service, workflow_id, step_id, task_id)
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
    wr = await ctrl_run_workflow(service, workflow_id, body)
    if not wr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return workflow_run_to_response(wr)
