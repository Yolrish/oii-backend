"""
Workflow API 用 Pydantic Schema
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# ---------- Task 结果（用于响应） ----------


class TaskResultContentSchema(BaseModel):
    """Task 执行结果内容"""
    type: str = "text"
    content: str = ""


# ---------- Task ----------


class TaskCreate(BaseModel):
    """创建 Task 请求"""
    name: str = ""
    description: str = ""
    creator: str = ""
    handler_path: str = ""
    params: Optional[Dict[str, Any]] = None
    on_before_path: str = ""
    on_start_path: str = ""
    on_done_path: str = ""
    on_retry_path: str = ""


class TaskUpdate(BaseModel):
    """更新 Task 请求（全部可选）"""
    name: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[str] = None
    handler_path: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    on_before_path: Optional[str] = None
    on_start_path: Optional[str] = None
    on_done_path: Optional[str] = None
    on_retry_path: Optional[str] = None


class TaskResponse(BaseModel):
    """Task 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    parent_step_id: str
    parent_workflow_id: str
    creator: str
    created_at: Optional[datetime] = None
    run_status: str
    handler_path: str
    params: Optional[Dict[str, Any]] = None
    on_before_path: str = ""
    on_start_path: str = ""
    on_done_path: str = ""
    on_retry_path: str = ""
    result: Optional[TaskResultContentSchema] = None


# ---------- Step ----------


class StepCreate(BaseModel):
    """创建 Step 请求（过程节点）"""
    name: str = ""
    description: str = ""
    creator: str = ""
    on_before_path: str = ""
    on_start_path: str = ""
    on_done_path: str = ""
    on_retry_path: str = ""


class StepUpdate(BaseModel):
    """更新 Step 请求（全部可选）"""
    name: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[str] = None
    on_before_path: Optional[str] = None
    on_start_path: Optional[str] = None
    on_done_path: Optional[str] = None
    on_retry_path: Optional[str] = None


class StepResponse(BaseModel):
    """Step 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    name: str
    description: str
    parent_workflow_id: str
    previous_step_id: str
    next_step_id: str
    creator: str
    created_at: Optional[datetime] = None
    tasks: List[TaskResponse] = []
    on_before_path: str = ""
    on_start_path: str = ""
    on_done_path: str = ""
    on_retry_path: str = ""


# ---------- Workflow ----------


class WorkflowCreate(BaseModel):
    """创建 Workflow 请求"""
    name: str = ""
    description: str = ""
    creator: str = ""


class WorkflowResponse(BaseModel):
    """Workflow 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    creator: str
    created_at: Optional[datetime] = None
    first_step_id: str
    end_step_id: str
    steps: List[StepResponse] = []
    task_results: Dict[str, TaskResultContentSchema] = {}


# ---------- 执行 ----------


class RunWorkflowRequest(BaseModel):
    """执行 Workflow 请求"""
    context: Optional[Dict[str, Any]] = None


class TaskResultSchema(BaseModel):
    """单条 Task 执行结果"""
    task_id: str
    success: bool
    data: Optional[TaskResultContentSchema] = None
    error: Optional[str] = None


class StepResultSchema(BaseModel):
    """Step 执行结果"""
    step_id: str
    success: bool
    task_results: List[TaskResultSchema] = []
    error: Optional[str] = None


class WorkflowRunResponse(BaseModel):
    """Workflow 执行结果响应"""
    workflow_id: str
    success: bool
    step_results: List[StepResultSchema] = []
    error: Optional[str] = None
