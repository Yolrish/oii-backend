"""
AI 指定格式 → Workflow 的映射

将 AI 返回的指定格式（WorkflowSpec）转为 Workflow/Step/Task，仅写入路径字符串，不解析为函数。
执行时由 WorkflowService 在 run_workflow / _run_step / _run_task 中通过 resolve_handler 将路径解析为 callable 再执行。
"""
from typing import Any, Dict, Optional

from ..models.models import Workflow, Step, Task
from .schemas import WorkflowSpec, StepSpec, TaskSpec


def _task_spec_to_task(spec: TaskSpec) -> Task:
    """TaskSpec → Task：仅写入 handler 与回调路径，不解析为 callable"""
    return Task(
        name=spec.name or "",
        handler_path=spec.handler or "",
        params=spec.params,
        on_before_path=spec.on_before or "",
        on_start_path=spec.on_start or "",
        on_done_path=spec.on_done or "",
        on_retry_path=spec.on_retry or "",
    )


def _step_spec_to_step(spec: StepSpec) -> Step:
    """StepSpec → Step：仅写入回调路径与 tasks"""
    return Step(
        name=spec.name or "",
        tasks=[_task_spec_to_task(t) for t in spec.tasks],
        on_before_path=spec.on_before or "",
        on_start_path=spec.on_start or "",
        on_done_path=spec.on_done or "",
        on_retry_path=spec.on_retry or "",
    )


def parse_ai_workflow(
    spec: WorkflowSpec,
    workflow_id: Optional[str] = None,
) -> Workflow:
    """
    将 AI 指定格式解析为 Workflow。
    只写入路径字符串，不解析为函数；执行时由服务按路径解析并执行。
    会填充各 Step 的 parent_workflow_id、previous_step_id、next_step_id 及各 Task 的 parent_workflow_id、parent_step_id。
    """
    steps = [_step_spec_to_step(s) for s in spec.steps]
    w = Workflow(
        id=workflow_id or "",
        name=spec.name or "",
        steps=steps,
    )
    if workflow_id:
        w.id = workflow_id
    for i, s in enumerate(w.steps):
        s.parent_workflow_id = w.id
        s.previous_step_id = w.steps[i - 1].id if i > 0 else ""
        s.next_step_id = w.steps[i + 1].id if i + 1 < len(w.steps) else ""
        for t in s.tasks:
            t.parent_workflow_id = w.id
            t.parent_step_id = s.id
    return w


def parse_ai_workflow_from_dict(
    data: Dict[str, Any],
    workflow_id: Optional[str] = None,
) -> Workflow:
    """从 dict（如 AI 返回的 JSON）解析为 Workflow；dict 需符合 WorkflowSpec 结构"""
    spec = dict_to_workflow_spec(data)
    return parse_ai_workflow(spec, workflow_id)


# ---------- 反向：Workflow → Spec（便于落库或回传给 AI） ----------


def _task_to_task_spec(task: Task) -> TaskSpec:
    """Task → TaskSpec（从路径字段写出）"""
    return TaskSpec(
        name=task.name,
        handler=task.handler_path or "",
        params=task.params if isinstance(task.params, dict) else {},
        on_before=task.on_before_path or "",
        on_start=task.on_start_path or "",
        on_done=task.on_done_path or "",
        on_retry=task.on_retry_path or "",
    )


def _step_to_step_spec(step: Step) -> StepSpec:
    """Step → StepSpec"""
    return StepSpec(
        name=step.name,
        tasks=[_task_to_task_spec(t) for t in step.tasks],
        on_before=step.on_before_path or "",
        on_start=step.on_start_path or "",
        on_done=step.on_done_path or "",
        on_retry=step.on_retry_path or "",
    )


def workflow_to_spec(workflow: Workflow) -> WorkflowSpec:
    """Workflow 转为 AI 指定格式（用于持久化或回传）"""
    return WorkflowSpec(
        name=workflow.name,
        steps=[_step_to_step_spec(s) for s in workflow.steps],
    )


# ---------- Spec 与 dict 互转（落库用） ----------


def workflow_spec_to_dict(spec: WorkflowSpec) -> Dict[str, Any]:
    """WorkflowSpec → 可写入 MongoDB 的 dict"""
    return {
        "name": spec.name,
        "execution_handler": spec.execution_handler,
        "steps": [
            {
                "name": s.name,
                "on_before": s.on_before,
                "on_start": s.on_start,
                "on_done": s.on_done,
                "on_retry": s.on_retry,
                "tasks": [
                    {
                        "name": t.name,
                        "handler": t.handler,
                        "params": t.params,
                        "on_before": t.on_before,
                        "on_start": t.on_start,
                        "on_done": t.on_done,
                        "on_retry": t.on_retry,
                    }
                    for t in s.tasks
                ],
            }
            for s in spec.steps
        ],
    }


def dict_to_workflow_spec(data: Dict[str, Any]) -> WorkflowSpec:
    """从 MongoDB 或 AI 返回的 dict 转为 WorkflowSpec"""
    steps_raw = data.get("steps") or []
    steps = []
    for s in steps_raw:
        tasks = [
            TaskSpec(
                name=t.get("name", ""),
                handler=t.get("handler", ""),
                params=t.get("params") or {},
                on_before=t.get("on_before", ""),
                on_start=t.get("on_start", ""),
                on_done=t.get("on_done", ""),
                on_retry=t.get("on_retry", ""),
            )
            for t in s.get("tasks") or []
        ]
        steps.append(
            StepSpec(
                name=s.get("name", ""),
                tasks=tasks,
                on_before=s.get("on_before", ""),
                on_start=s.get("on_start", ""),
                on_done=s.get("on_done", ""),
                on_retry=s.get("on_retry", ""),
            )
        )
    return WorkflowSpec(
        name=data.get("name", ""),
        steps=steps,
        execution_handler=data.get("execution_handler", ""),
    )
