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
    STEP_TYPE_START,
    STEP_TYPE_PROCESS,
    STEP_TYPE_END,
    TASK_RUN_STATUS_PENDING,
    TASK_RUN_STATUS_RUNNING,
    TASK_RUN_STATUS_SUCCESS,
    TASK_RUN_STATUS_FAILED,
)
from ..models.persistence import resolve_handler
from ..repositories import (
    save_workflow_meta,
    load_workflow_from_db,
    save_step,
    update_step,
    save_task,
    update_task,
    update_task_result,
    save_workflow_task_result,
    delete_step_cascade,
    delete_task_from_db,
    delete_workflow_cascade,
)


def _resolve_path(path: str) -> Optional[Callable[..., Any]]:
    """将模块路径解析为 callable，空串返回 None"""
    if not path or not path.strip():
        return None
    return resolve_handler(path.strip())


def _invoke_callback(
    cb: Optional[Callable[..., Any]], *args: Any, **kwargs: Any
) -> Any:
    """调用回调（sync 或 async），由调用方负责 await。"""
    if cb is None:
        return None
    return cb(*args, **kwargs)


async def _invoke_callback_async(
    cb: Optional[Callable[..., Any]], *args: Any, **kwargs: Any
) -> Any:
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
    - 当已配置 db 且 persist_enabled 时，create/add/edit/delete 等操作完成后会自动同步到数据库
    - Web 后端场景：_workflows 为缓存，get_workflow/run_workflow 等若内存未命中则从 DB 按需加载，便于跨请求、多实例、重启后仍可操作
    """

    def __init__(
        self,
        config: Optional[WorkflowConfig] = None,
        db: Optional[Any] = None,
    ) -> None:
        self.config = config or WorkflowConfig()
        self._db = db
        # 内存缓存；未命中时若已开启持久化则从 DB 按需加载（见 _ensure_workflow）
        self._workflows: Dict[str, Workflow] = {}

    def _wf_coll(self) -> str:
        return self.config.workflow_collection_name

    def _step_coll(self) -> str:
        return self.config.step_collection_name

    def _task_coll(self) -> str:
        return self.config.task_collection_name

    async def _ensure_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """若 workflow 在内存则直接返回；否则若已开启持久化则从 DB 加载并放入缓存后返回；否则返回 None"""
        if workflow_id in self._workflows:
            return self._workflows[workflow_id]
        if self._db and self.config.persist_enabled:
            w = await load_workflow_from_db(
                self._db,
                self._wf_coll(),
                self._step_coll(),
                self._task_coll(),
                workflow_id,
            )
            if w:
                self._workflows[workflow_id] = w
            return w
        return None

    # ---------- Workflow CRUD ----------

    async def create_workflow(
        self,
        name: str = "",
        creator: str = "",
        description: str = "",
    ) -> Workflow:
        """创建新的 workflow，并默认创建起始节点与结束节点（不可删、不可添加 task）"""
        now = datetime.utcnow()
        w = Workflow(
            name=name,
            description=description or "",
            creator=creator or "",
            created_at=now,
        )
        # 默认创建起始节点与结束节点
        start_step = Step(
            name="Start",
            type=STEP_TYPE_START,
            description="",
            parent_workflow_id=w.id,
            previous_step_id="",
            next_step_id="",  # 稍后设为 end_step.id
            creator=creator or "",
            created_at=now,
        )
        end_step = Step(
            name="End",
            type=STEP_TYPE_END,
            description="",
            parent_workflow_id=w.id,
            previous_step_id=start_step.id,
            next_step_id="",
            creator=creator or "",
            created_at=now,
        )
        start_step.next_step_id = end_step.id
        w.steps = [start_step, end_step]
        w.first_step_id = start_step.id
        w.end_step_id = end_step.id
        self._workflows[w.id] = w
        if self._db and self.config.persist_enabled:
            await save_workflow_meta(self._db, self._wf_coll(), w)
            await save_step(self._db, self._step_coll(), start_step)
            await save_step(self._db, self._step_coll(), end_step)
        return w

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """根据 id 获取 workflow；若不在内存且已开启持久化则从 DB 按需加载"""
        return await self._ensure_workflow(workflow_id)

    async def delete_workflow(self, workflow_id: str) -> bool:
        """删除 workflow，并级联删除 step 表、task 表中关联行；若仅存在于 DB 也会执行级联删除"""
        if workflow_id in self._workflows:
            if self._db and self.config.persist_enabled:
                await delete_workflow_cascade(
                    self._db,
                    self._wf_coll(),
                    self._step_coll(),
                    self._task_coll(),
                    workflow_id,
                )
            del self._workflows[workflow_id]
            return True
        if self._db and self.config.persist_enabled:
            ok = await delete_workflow_cascade(
                self._db,
                self._wf_coll(),
                self._step_coll(),
                self._task_coll(),
                workflow_id,
            )
            return ok
        return False

    async def persist_workflow(self, workflow_id: str) -> bool:
        """将当前 workflow 全量同步到三张表（逐表写入）；未配置持久化时返回 False"""
        if not self._db or not self.config.persist_enabled:
            return False
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return False
        await save_workflow_meta(self._db, self._wf_coll(), w)
        for s in w.steps:
            await save_step(self._db, self._step_coll(), s)
            for t in s.tasks:
                await save_task(self._db, self._task_coll(), t)
        return True

    # ---------- Step 操作 ----------

    async def add_step(
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
        """在 workflow 中结束节点前添加过程 step（链：… -> 新step -> 结束）"""
        w = await self._ensure_workflow(workflow_id)
        if not w or not w.end_step_id:
            return None
        end_step = self._get_step(workflow_id, w.end_step_id)
        if not end_step:
            return None
        # 结束节点前一个 step（可能是起始或某个过程 step）
        prev_id = end_step.previous_step_id or ""
        now = datetime.utcnow()
        step = Step(
            name=name,
            description=description or "",
            type=STEP_TYPE_PROCESS,
            parent_workflow_id=workflow_id,
            previous_step_id=prev_id,
            next_step_id=end_step.id,
            creator=creator or "",
            created_at=now,
            on_before_path=on_before_path or "",
            on_start_path=on_start_path or "",
            on_done_path=on_done_path or "",
            on_retry_path=on_retry_path or "",
        )
        end_step.previous_step_id = step.id
        if prev_id:
            for s in w.steps:
                if s.id == prev_id:
                    s.next_step_id = step.id
                    break
        # 插入到结束节点前
        w.steps.insert(len(w.steps) - 1, step)
        if self._db and self.config.persist_enabled:
            await save_step(self._db, self._step_coll(), step)
            await update_step(self._db, self._step_coll(), end_step)
            if prev_id:
                for s in w.steps:
                    if s.id == prev_id:
                        await update_step(self._db, self._step_coll(), s)
                        break
        return step

    async def add_step_after(
        self,
        workflow_id: str,
        after_step_id: str,
        name: str = "",
        description: str = "",
        creator: str = "",
        on_before_path: str = "",
        on_start_path: str = "",
        on_done_path: str = "",
        on_retry_path: str = "",
    ) -> Optional[Step]:
        """在指定 step 后方插入新的过程 step；不可在结束节点后插入"""
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return None
        if after_step_id == w.end_step_id:
            return None  # 结束节点后不可插入
        after_index = -1
        after_step = None
        for i, s in enumerate(w.steps):
            if s.id == after_step_id:
                after_index = i
                after_step = s
                break
        if after_index < 0 or after_step is None:
            return None
        now = datetime.utcnow()
        next_step_id = after_step.next_step_id or ""
        step = Step(
            name=name,
            description=description or "",
            type=STEP_TYPE_PROCESS,
            parent_workflow_id=workflow_id,
            previous_step_id=after_step_id,
            next_step_id=next_step_id,
            creator=creator or "",
            created_at=now,
            on_before_path=on_before_path or "",
            on_start_path=on_start_path or "",
            on_done_path=on_done_path or "",
            on_retry_path=on_retry_path or "",
        )
        after_step.next_step_id = step.id
        if next_step_id:
            for s0 in w.steps:
                if s0.id == next_step_id:
                    s0.previous_step_id = step.id
                    break
        w.steps.insert(after_index + 1, step)
        if self._db and self.config.persist_enabled:
            await save_step(self._db, self._step_coll(), step)
            await update_step(self._db, self._step_coll(), after_step)
            if next_step_id:
                for s0 in w.steps:
                    if s0.id == next_step_id:
                        await update_step(self._db, self._step_coll(), s0)
                        break
        return step

    async def delete_step(self, workflow_id: str, step_id: str) -> bool:
        """删除指定 step；起始节点与结束节点不可删除"""
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return False
        if step_id == w.first_step_id or step_id == w.end_step_id:
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
                if self._db and self.config.persist_enabled:
                    await delete_step_cascade(
                        self._db, self._step_coll(), self._task_coll(), step_id
                    )
                if self._db and self.config.persist_enabled and (prev_id or next_id):
                    for s0 in w.steps:
                        if s0.id == prev_id or s0.id == next_id:
                            await update_step(self._db, self._step_coll(), s0)
                return True
        return False

    async def edit_step(
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
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return None
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
        if self._db and self.config.persist_enabled:
            await update_step(self._db, self._step_coll(), step)
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

    async def add_task(
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
        """在 step 内添加 task；起始节点与结束节点不可添加 task"""
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return None
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        if step.type in (STEP_TYPE_START, STEP_TYPE_END):
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
        if self._db and self.config.persist_enabled:
            await save_task(self._db, self._task_coll(), task)
        return task

    async def delete_task(self, workflow_id: str, step_id: str, task_id: str) -> bool:
        """删除 step 内指定 task；起始/结束节点上不允许删除（无 task 或防御性校验）"""
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return False
        step = self._get_step(workflow_id, step_id)
        if not step:
            return False
        if step.type in (STEP_TYPE_START, STEP_TYPE_END):
            return False
        for i, t in enumerate(step.tasks):
            if t.id == task_id:
                step.tasks.pop(i)
                if self._db and self.config.persist_enabled:
                    await delete_task_from_db(self._db, self._task_coll(), task_id)
                return True
        return False

    async def edit_task(
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
        """编辑 task（名称、描述、创建者、handler 路径、参数与回调路径）；起始/结束节点上无 task，直接返回 None"""
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return None
        step = self._get_step(workflow_id, step_id)
        if not step:
            return None
        if step.type in (STEP_TYPE_START, STEP_TYPE_END):
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
                if self._db and self.config.persist_enabled:
                    await update_task(self._db, self._task_coll(), t)
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
            if (
                self.config.max_task_concurrent
                and 0 < self.config.max_task_concurrent < len(coros)
            ):
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
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return None
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
        w = await self._ensure_workflow(workflow_id)
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
                                self._task_coll(),
                                tr.task_id,
                                TASK_RUN_STATUS_SUCCESS,
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
        w = await self._ensure_workflow(workflow_id)
        if not w:
            return None
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
                                self._task_coll(),
                                tr.task_id,
                                TASK_RUN_STATUS_SUCCESS,
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
