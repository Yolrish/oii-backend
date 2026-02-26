"""
Workflow 服务

创建/管理仅使用字符串（handler 路径、回调路径）；执行时将路径解析为函数再执行。
提供工作流的创建、步骤/任务的增删改与重执行，以及整链串行（step）+ 步骤内并行（task）的执行逻辑。
"""
import asyncio
from datetime import datetime
from typing import Any, Callable, Optional, List, Dict

from ..configs.config import WorkflowConfig
from ..models.models import (
    Workflow,
    Step,
    Task,
    StepResult,
    TaskResult,
    TaskResultContent,
    WorkflowResult,
    TASK_RUN_STATUS_PENDING,
    TASK_RUN_STATUS_RUNNING,
    TASK_RUN_STATUS_SUCCESS,
    TASK_RUN_STATUS_FAILED,
)
from ..models.persistence import resolve_handler
from ..repositories import save_workflow_task_result


def _resolve_path(path: str) -> Optional[Callable[..., Any]]:
    """将模块路径解析为 callable，空串返回 None"""
    if not path or not path.strip():
        return None
    return resolve_handler(path.strip())


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

    - 创建 Workflow / Step / Task 时只传字符串（handler 路径、回调路径），不传函数
    - 执行时由服务将路径解析为 callable 再执行
    - 支持可选的数据库持久化（需 config.persist_enabled 并注入 db）
    """

    def __init__(
        self,
        config: Optional[WorkflowConfig] = None,
        db: Optional[Any] = None,
    ) -> None:
        self.config = config or WorkflowConfig()
        self._db = db
        self._workflows: Dict[str, Workflow] = {}

    # ---------- Workflow CRUD ----------

    def create_workflow(
        self,
        name: str = "",
        creator: str = "",
        description: str = "",
    ) -> Workflow:
        """创建新的 workflow（含 id、创建者、创建时间、名称、描述）"""
        now = datetime.utcnow()
        w = Workflow(
            name=name,
            description=description or "",
            creator=creator or "",
            created_at=now,
        )
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

    def add_step(
        self,
        workflow_id: str,
        name: str = "",
        description: str = "",
        creator: str = "",
        on_before_path: str = "",
        on_start_path: str = "",
        on_done_path: str = "",
        on_retry_path: str = "",
    ) -> Optional[Step]:
        """在 workflow 末尾添加 step（含父 workflow id、上/下一个 step id、创建者、创建时间、名称、描述）"""
        w = self._workflows.get(workflow_id)
        if not w:
            return None
        now = datetime.utcnow()
        previous_step_id = w.steps[-1].id if w.steps else ""
        step = Step(
            name=name,
            description=description or "",
            parent_workflow_id=workflow_id,
            previous_step_id=previous_step_id,
            next_step_id="",
            creator=creator or "",
            created_at=now,
            on_before_path=on_before_path or "",
            on_start_path=on_start_path or "",
            on_done_path=on_done_path or "",
            on_retry_path=on_retry_path or "",
        )
        if w.steps:
            w.steps[-1].next_step_id = step.id
        w.steps.append(step)
        return step

    def delete_step(self, workflow_id: str, step_id: str) -> bool:
        """删除指定 step，并维护链上前后的 previous_step_id / next_step_id"""
        w = self._workflows.get(workflow_id)
        if not w:
            return False
        for i, s in enumerate(w.steps):
            if s.id == step_id:
                prev_id = s.previous_step_id
                next_id = s.next_step_id
                w.steps.pop(i)
                if prev_id:
                    for s0 in w.steps:
                        if s0.id == prev_id:
                            s0.next_step_id = next_id
                            break
                if next_id:
                    for s0 in w.steps:
                        if s0.id == next_id:
                            s0.previous_step_id = prev_id
                            break
                return True
        return False

    def edit_step(
        self,
        workflow_id: str,
        step_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        creator: Optional[str] = None,
        on_before_path: Optional[str] = None,
        on_start_path: Optional[str] = None,
        on_done_path: Optional[str] = None,
        on_retry_path: Optional[str] = None,
    ) -> Optional[Step]:
        """编辑 step（名称、描述、创建者与回调路径）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        if name is not None:
            step.name = name
        if description is not None:
            step.description = description
        if creator is not None:
            step.creator = creator
        if on_before_path is not None:
            step.on_before_path = on_before_path
        if on_start_path is not None:
            step.on_start_path = on_start_path
        if on_done_path is not None:
            step.on_done_path = on_done_path
        if on_retry_path is not None:
            step.on_retry_path = on_retry_path
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
        name: str = "",
        description: str = "",
        creator: str = "",
        handler_path: str = "",
        params: Any = None,
        on_before_path: str = "",
        on_start_path: str = "",
        on_done_path: str = "",
        on_retry_path: str = "",
    ) -> Optional[Task]:
        """在 step 内添加 task（含父 step/workflow id、创建者、创建时间、名称、描述、函数字符信息）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        now = datetime.utcnow()
        task = Task(
            name=name,
            description=description or "",
            parent_step_id=step_id,
            parent_workflow_id=workflow_id,
            creator=creator or "",
            created_at=now,
            run_status=TASK_RUN_STATUS_PENDING,
            handler_path=handler_path or "",
            params=params,
            on_before_path=on_before_path or "",
            on_start_path=on_start_path or "",
            on_done_path=on_done_path or "",
            on_retry_path=on_retry_path or "",
        )
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
        description: Optional[str] = None,
        creator: Optional[str] = None,
        handler_path: Optional[str] = None,
        params: Any = None,
        on_before_path: Optional[str] = None,
        on_start_path: Optional[str] = None,
        on_done_path: Optional[str] = None,
        on_retry_path: Optional[str] = None,
    ) -> Optional[Task]:
        """编辑 task（名称、描述、创建者、handler 路径、参数与回调路径）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        for t in step.tasks:
            if t.id == task_id:
                if name is not None:
                    t.name = name
                if description is not None:
                    t.description = description
                if creator is not None:
                    t.creator = creator
                if handler_path is not None:
                    t.handler_path = handler_path
                if params is not None:
                    t.params = params
                if on_before_path is not None:
                    t.on_before_path = on_before_path
                if on_start_path is not None:
                    t.on_start_path = on_start_path
                if on_done_path is not None:
                    t.on_done_path = on_done_path
                if on_retry_path is not None:
                    t.on_retry_path = on_retry_path
                return t
        return None

    # ---------- 执行：Task（执行时解析路径为函数） ----------

    async def _run_task(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """执行单个 task：更新 run_status，将 handler_path 解析为 callable 后执行，并写入 result"""
        result = TaskResult(task_id=task.id)
        task.run_status = TASK_RUN_STATUS_RUNNING
        on_before = _resolve_path(task.on_before_path)
        on_start = _resolve_path(task.on_start_path)
        on_done = _resolve_path(task.on_done_path)
        try:
            await _invoke_callback_async(on_before, task, context)
            await _invoke_callback_async(on_start, task, context)
            func = _resolve_path(task.handler_path)
            if func:
                params = task.params if isinstance(task.params, dict) else {}
                out = _invoke_callback(func, context, **params)
                if asyncio.iscoroutine(out):
                    out = await out
                result.data = TaskResultContent.from_dict(out)
            else:
                result.data = TaskResultContent(type="text", content="")
            result.success = True
            task.run_status = TASK_RUN_STATUS_SUCCESS
            task.result = result.data
        except Exception as e:
            result.error = str(e)
            task.run_status = TASK_RUN_STATUS_FAILED
        await _invoke_callback_async(on_done, task, context, result)
        return result

    async def _run_task_retry(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """重执行 task，先触发 on_retry_path 对应的回调"""
        on_retry = _resolve_path(task.on_retry_path)
        await _invoke_callback_async(on_retry, task, context)
        return await self._run_task(task, context)

    # ---------- 执行：Step ----------

    async def _run_step(self, step: Step, context: Dict[str, Any]) -> StepResult:
        """执行 step：将回调路径解析为 callable 后执行"""
        sr = StepResult(step_id=step.id)
        on_before = _resolve_path(step.on_before_path)
        on_start = _resolve_path(step.on_start_path)
        on_done = _resolve_path(step.on_done_path)
        try:
            await _invoke_callback_async(on_before, step, context)
            await _invoke_callback_async(on_start, step, context)
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
        await _invoke_callback_async(on_done, step, context, sr)
        return sr

    async def re_run_step(
        self, workflow_id: str, step_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[StepResult]:
        """重执行指定 step（先触发 step.on_retry_path 对应回调）"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        ctx = context or {}
        on_retry = _resolve_path(step.on_retry_path)
        await _invoke_callback_async(on_retry, step, ctx)
        return await self._run_step(step, ctx)

    # ---------- 执行：Workflow ----------

    async def run_workflow(
        self, workflow_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowResult]:
        """按链顺序串行执行所有 step，每个 step 内 task 并行执行；成功完成的 task 结果会写入内存并可选持久化到 DB"""
        w = self._workflows.get(workflow_id)
        if not w:
            return None
        ctx = context or {}
        wr = WorkflowResult(workflow_id=w.id)
        try:
            for step in w.steps:
                sr = await self._run_step(step, ctx)
                wr.step_results.append(sr)
                # 将执行成功且带结果的 task 写入 workflow.task_results 并可选落库
                for tr in sr.task_results:
                    if tr.success and tr.data is not None:
                        w.task_results[tr.task_id] = tr.data
                        if self._db and self.config.persist_enabled:
                            await save_workflow_task_result(
                                self._db,
                                self.config.collection_name,
                                w.id,
                                tr.task_id,
                                tr.data,
                            )
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
        """重执行指定 task（先触发 on_retry_path 对应回调）；成功则更新并可选持久化该 task 结果"""
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        for t in step.tasks:
            if t.id == task_id:
                tr = await self._run_task_retry(t, context or {})
                if tr.success and tr.data is not None:
                    w = self._workflows.get(workflow_id)
                    if w:
                        w.task_results[tr.task_id] = tr.data
                        if self._db and self.config.persist_enabled:
                            await save_workflow_task_result(
                                self._db,
                                self.config.collection_name,
                                w.id,
                                tr.task_id,
                                tr.data,
                            )
                return tr
        return None


_default_service: Optional[WorkflowService] = None


def get_default_service() -> WorkflowService:
    """获取默认单例 WorkflowService"""
    global _default_service
    if _default_service is None:
        _default_service = WorkflowService()
    return _default_service


def create_workflow_service(
    config: Optional[WorkflowConfig] = None,
    db: Optional[Any] = None,
) -> WorkflowService:
    """创建 WorkflowService 实例"""
    return WorkflowService(config=config, db=db)
