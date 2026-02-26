"""
Workflow 数据模型

Workflow -> Step（链式串行）-> Task（Step 内并行）
Step/Task 均支持：执行前、开始执行、执行完成、重新执行 的回调接口。
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional, List
import uuid


# ---------- 回调类型 ----------

# Step 回调：参数为 (step, context) 或 (step_id, context)，可选 async
StepCallback = Callable[..., Any]  # 支持 sync 或 async，由调用方 await 或 run_in_executor
TaskCallback = Callable[..., Any]


@dataclass
class StepCallbacks:
    """
    Step 生命周期回调
    所有回调均为可选；若为异步函数则会在执行时 await。
    """
    # 执行前（即将进入该 step 时）
    on_before: Optional[StepCallback] = None
    # 开始执行（step 内 tasks 开始前）
    on_start: Optional[StepCallback] = None
    # 执行完成（step 内所有 task 完成后）
    on_done: Optional[StepCallback] = None
    # 重新执行（重跑该 step 时）
    on_retry: Optional[StepCallback] = None


@dataclass
class TaskCallbacks:
    """
    Task 生命周期回调
    所有回调均为可选。
    """
    # 执行前
    on_before: Optional[TaskCallback] = None
    # 开始执行
    on_start: Optional[TaskCallback] = None
    # 执行完成
    on_done: Optional[TaskCallback] = None
    # 重新执行
    on_retry: Optional[TaskCallback] = None


# ---------- Task ----------

@dataclass
class Task:
    """
    单个任务
    执行由外部传入的 callable（可带参数），支持增删改、重执行与回调。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    # 外部传入的可执行对象：() -> Any 或 (context) -> Any，支持 sync/async
    func: Optional[Callable[..., Any]] = None
    # 传给 func 的额外参数（kwargs 或 args，由具体执行器约定）
    params: Any = None
    callbacks: TaskCallbacks = field(default_factory=TaskCallbacks)

    def __post_init__(self) -> None:
        if self.callbacks is None:
            self.callbacks = TaskCallbacks()


@dataclass
class TaskResult:
    """Task 执行结果"""
    task_id: str = ""
    success: bool = False
    data: Any = None
    error: Optional[str] = None


# ---------- Step ----------

@dataclass
class Step:
    """
    工作流步骤
    包含多个 Task，步骤内 Task 并行执行；步骤之间按顺序串行。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    tasks: List[Task] = field(default_factory=list)
    callbacks: StepCallbacks = field(default_factory=StepCallbacks)

    def __post_init__(self) -> None:
        if self.tasks is None:
            self.tasks = []
        if self.callbacks is None:
            self.callbacks = StepCallbacks()


@dataclass
class StepResult:
    """Step 执行结果（包含该 step 内所有 task 的结果）"""
    step_id: str = ""
    success: bool = False
    task_results: List[TaskResult] = field(default_factory=list)
    error: Optional[str] = None


# ---------- Workflow ----------

@dataclass
class Workflow:
    """
    动态工作流
    Step 以链的形式连接，串行执行；每个 Step 内多个 Task 并行执行。
    支持灵活添加、删除、编辑、重执行 Step 与 Task。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    steps: List[Step] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.steps is None:
            self.steps = []


@dataclass
class WorkflowResult:
    """Workflow 整体执行结果"""
    workflow_id: str = ""
    success: bool = False
    step_results: List[StepResult] = field(default_factory=list)
    error: Optional[str] = None
