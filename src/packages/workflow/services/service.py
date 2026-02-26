"""
Workflow 服务

提供工作流的创建、步骤/任务的增删改与重执行，以及整链串行（step）+ 步骤内并行（task）的执行逻辑。
Step/Task 在执行前、开始、完成、重执行时触发对应回调。
"""
import asyncio
from typing import Any, Callable, Optional, List, Dict

from ..configs.config import WorkflowConfig
from ..models.models import (
    Workflow,
    Step,
    Task,
    StepCallbacks,
    TaskCallbacks,
    StepResult,
    TaskResult,
    WorkflowResult,
)


def _invoke_callback(cb: Optional[Callable[..., Any]], *args: Any, **kwargs: Any) -> Any:
    """调用回调（sync 或 async），由调用方负责 await。"""
    if cb is None:
        return None
    return cb(*args, **kwargs)


async def _invoke_callback_async(cb: Optional[Callable[..., Any]], *args: Any, **kwargs: Any) -> Any:
    """异步调用回调：若为 coroutine 则 await，否则直接返回。"""
    if cb is None:
        return None
    result = cb(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


class WorkflowService:
    """
    动态 Workflow 服务

    - 创建 Workflow，管理 Step（链式串行）、Task（Step 内并行）
    - Step/Task 支持：添加、删除、编辑、重执行
    - 执行前、开始执行、执行完成、重新执行 的回调接口
    """

    def __init__(self, config: Optional[WorkflowConfig] = None) -> None:
        self.config = config or WorkflowConfig()
        self._workflows: Dict[str, Workflow] = {}

    # ---------- Workflow CRUD ----------

    def create_workflow(self, name: str = "") -> Workflow:
        """创建新的 workflow"""
        w = Workflow(name=name)
        self._workflows[w.id] = w
        return w

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """根据 id 获取 workflow"""
        return self._workflows.get(workflow_id)

    def delete_workflow(self, workflow_id: str) -> bool:
        """删除 workflow"""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    # ---------- Step 操作 ----------

    def add_step(self, workflow_id: str, name: str = "", callbacks: Optional[StepCallbacks] = None) -> Optional[Step]:
        """在 workflow 末尾添加 step"""
        w = self._workflows.get(workflow_id)
        if not w:
            return None
        step = Step(name=name, callbacks=callbacks or StepCallbacks())
        w.steps.append(step)
        return step

    def delete_step(self, workflow_id: str, step_id: str) -> bool:
        """删除指定 step"""
        w = self._workflows.get(workflow_id)
        if not w:
            return False
        for i, s in enumerate(w.steps):
            if s.id == step_id:
                w.steps.pop(i)
                return True
        return False

    def edit_step(
        self,
        workflow_id: str,
        step_id: str,
        name: Optional[str] = None,
        callbacks: Optional[StepCallbacks] = None,
    ) -> Optional[Step]:
        """编辑 step（名称、回调等）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        if name is not None:
            step.name = name
        if callbacks is not None:
            step.callbacks = callbacks
        return step

    def _get_step(self, workflow_id: str, step_id: str) -> Optional[Step]:
        w = self._workflows.get(workflow_id)
        if not w:
            return None
        for s in w.steps:
            if s.id == step_id:
                return s
        return None

    # ---------- Task 操作 ----------

    def add_task(
        self,
        workflow_id: str,
        step_id: str,
        func: Optional[Callable[..., Any]] = None,
        name: str = "",
        params: Any = None,
        callbacks: Optional[TaskCallbacks] = None,
    ) -> Optional[Task]:
        """在 step 内添加 task"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        task = Task(name=name, func=func, params=params, callbacks=callbacks or TaskCallbacks())
        step.tasks.append(task)
        return task

    def delete_task(self, workflow_id: str, step_id: str, task_id: str) -> bool:
        """删除 step 内指定 task"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return False
        for i, t in enumerate(step.tasks):
            if t.id == task_id:
                step.tasks.pop(i)
                return True
        return False

    def edit_task(
        self,
        workflow_id: str,
        step_id: str,
        task_id: str,
        name: Optional[str] = None,
        func: Optional[Callable[..., Any]] = None,
        params: Any = None,
        callbacks: Optional[TaskCallbacks] = None,
    ) -> Optional[Task]:
        """编辑 task"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        for t in step.tasks:
            if t.id == task_id:
                if name is not None:
                    t.name = name
                if func is not None:
                    t.func = func
                if params is not None:
                    t.params = params
                if callbacks is not None:
                    t.callbacks = callbacks
                return t
        return None

    # ---------- 执行：Task ----------

    async def _run_task(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """执行单个 task，触发 on_before / on_start / on_done（重执行时还有 on_retry）"""
        result = TaskResult(task_id=task.id)
        try:
            await _invoke_callback_async(task.callbacks.on_before, task, context)
            await _invoke_callback_async(task.callbacks.on_start, task, context)
            if task.func:
                params = task.params if isinstance(task.params, dict) else {}
                out = _invoke_callback(task.func, context, **params)
                if asyncio.iscoroutine(out):
                    out = await out
                result.data = out
            result.success = True
        except Exception as e:
            result.error = str(e)
        await _invoke_callback_async(task.callbacks.on_done, task, context, result)
        return result

    async def _run_task_retry(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """重执行 task，先触发 on_retry"""
        await _invoke_callback_async(task.callbacks.on_retry, task, context)
        return await self._run_task(task, context)

    # ---------- 执行：Step ----------

    async def _run_step(self, step: Step, context: Dict[str, Any]) -> StepResult:
        """执行 step：先 step 回调，再并行执行所有 task"""
        sr = StepResult(step_id=step.id)
        try:
            await _invoke_callback_async(step.callbacks.on_before, step, context)
            await _invoke_callback_async(step.callbacks.on_start, step, context)
            coros = [self._run_task(t, context) for t in step.tasks]
            if self.config.max_task_concurrent and 0 < self.config.max_task_concurrent < len(coros):
                sem = asyncio.Semaphore(self.config.max_task_concurrent)
                async def bounded(coro):
                    async with sem:
                        return await coro
                task_results = await asyncio.gather(*[bounded(c) for c in coros])
            else:
                task_results = await asyncio.gather(*coros)
            sr.task_results = list(task_results)
            sr.success = all(r.success for r in task_results)
        except Exception as e:
            sr.error = str(e)
        await _invoke_callback_async(step.callbacks.on_done, step, context, sr)
        return sr

    async def re_run_step(
        self, workflow_id: str, step_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[StepResult]:
        """重执行指定 step（会先触发 step.on_retry，然后各 task 按正常流程执行）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        ctx = context or {}
        await _invoke_callback_async(step.callbacks.on_retry, step, ctx)
        return await self._run_step(step, ctx)

    # ---------- 执行：Workflow ----------

    async def run_workflow(
        self, workflow_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowResult]:
        """
        按链顺序串行执行所有 step，每个 step 内 task 并行执行。
        """
        w = self._workflows.get(workflow_id)
        if not w:
            return None
        ctx = context or {}
        wr = WorkflowResult(workflow_id=w.id)
        try:
            for step in w.steps:
                sr = await self._run_step(step, ctx)
                wr.step_results.append(sr)
                if not sr.success:
                    wr.error = sr.error or "step failed"
                    break
            wr.success = not wr.error and all(sr.success for sr in wr.step_results)
        except Exception as e:
            wr.error = str(e)
        return wr

    async def re_run_task(
        self,
        workflow_id: str,
        step_id: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskResult]:
        """重执行指定 task（触发 task.on_retry 后执行）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        for t in step.tasks:
            if t.id == task_id:
                return await self._run_task_retry(t, context or {})
        return None


_default_service: Optional[WorkflowService] = None


def get_default_service() -> WorkflowService:
    """获取默认单例 WorkflowService"""
    global _default_service
    if _default_service is None:
        _default_service = WorkflowService()
    return _default_service


def create_workflow_service(config: Optional[WorkflowConfig] = None) -> WorkflowService:
    """创建 WorkflowService 实例"""
    return WorkflowService(config=config)
