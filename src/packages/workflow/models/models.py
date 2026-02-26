"""
Workflow 数据模型

Workflow -> Step（链式串行）-> Task（Step 内并行）
创建/存储时仅使用字符串（handler 路径、回调路径）；执行时由服务将字符串解析为函数再执行。
Task 执行结果统一为 { type, content } 格式，用于持久化到数据库。
Workflow/Step/Task 均含：id、创建者、创建时间、名称、描述及关联 id 等存储所需字段。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid


# ---------- Task 结果内容（持久化格式） ----------

TaskResultType = Literal["text", "image", "video", "audio"]

# 支持的 type 取值，用于校验
TASK_RESULT_TYPES: tuple = ("text", "image", "video", "audio")


def _normalize_result_type(t: str) -> str:
    """将 type 规范为 text/image/video/audio 之一，否则退回 text"""
    if t in TASK_RESULT_TYPES:
        return t
    return "text"


@dataclass
class TaskResultContent:
    """
    Task 结果的内容格式（可序列化，用于落库）
    - type: 内容类型，取值为 text | image | video | audio
    - content: 文本内容或文件服务器 URL（字符串）
    """
    type: str = "text"  # text | image | video | audio
    content: str = ""

    def __post_init__(self) -> None:
        self.type = _normalize_result_type(self.type)

    def to_dict(self) -> Dict[str, str]:
        """转为可写入 DB 的 dict"""
        return {"type": self.type, "content": self.content or ""}

    @classmethod
    def from_dict(cls, data: Any) -> "TaskResultContent":
        """从 dict 或 handler 返回值构造；非法则返回 type=text, content 为 str(data)"""
        if data is None:
            return cls(type="text", content="")
        if isinstance(data, TaskResultContent):
            return data
        if isinstance(data, dict):
            t = data.get("type")
            c = data.get("content")
            return cls(
                type=_normalize_result_type(str(t) if t is not None else "text"),
                content=str(c) if c is not None else "",
            )
        return cls(type="text", content=str(data))


# ---------- Task 运行状态 ----------

TASK_RUN_STATUS_PENDING = "pending"
TASK_RUN_STATUS_RUNNING = "running"
TASK_RUN_STATUS_SUCCESS = "success"
TASK_RUN_STATUS_FAILED = "failed"


# ---------- Task ----------

@dataclass
class Task:
    """
    单个任务
    存储：id、父 step/workflow id、创建者、创建时间、运行状态、名称、描述、函数字符信息（handler_path 等）、执行结果。
    执行时由服务将 handler_path 解析为 callable 再执行。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    # 父 step 与父 workflow 的 id
    parent_step_id: str = ""
    parent_workflow_id: str = ""
    # 创建者、创建时间
    creator: str = ""
    created_at: Optional[datetime] = None
    # 运行状态：pending | running | success | failed
    run_status: str = TASK_RUN_STATUS_PENDING
    # 要执行的函数的模块路径（函数字符信息）
    handler_path: str = ""
    params: Any = None
    # 生命周期回调的模块路径
    on_before_path: str = ""
    on_start_path: str = ""
    on_done_path: str = ""
    on_retry_path: str = ""
    # 最近一次执行结果（与 Workflow.task_results 中该 task_id 对应项一致）
    result: Optional[TaskResultContent] = None


@dataclass
class TaskResult:
    """
    Task 执行结果
    data 为 TaskResultContent 或可被 TaskResultContent.from_dict 解析的返回值，便于持久化 { type, content }。
    """
    task_id: str = ""
    success: bool = False
    data: Optional[TaskResultContent] = None  # 统一为 { type, content } 格式
    error: Optional[str] = None


# ---------- Step ----------

@dataclass
class Step:
    """
    工作流步骤
    存储：id、父 workflow id、上一个/下一个 step id、创建者、创建时间、拥有的 task id 列表、名称、描述。
    步骤内 Task 并行，步骤间按 previous/next 串行。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    # 父 workflow、链式前后 step
    parent_workflow_id: str = ""
    previous_step_id: str = ""
    next_step_id: str = ""
    creator: str = ""
    created_at: Optional[datetime] = None
    tasks: List[Task] = field(default_factory=list)
    # 生命周期回调的模块路径
    on_before_path: str = ""
    on_start_path: str = ""
    on_done_path: str = ""
    on_retry_path: str = ""

    def __post_init__(self) -> None:
        if self.tasks is None:
            self.tasks = []

    @property
    def task_ids(self) -> List[str]:
        """拥有的 task 的 id 列表"""
        return [t.id for t in self.tasks]


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
    存储：id、创建者、创建时间、拥有的 step id 列表、名称、描述。
    Step 以链形式串行执行，Step 内 Task 并行。
    task_results: 已执行 task 的结果，key 为 task_id，与 DB 一致。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    creator: str = ""
    created_at: Optional[datetime] = None
    steps: List[Step] = field(default_factory=list)
    task_results: Dict[str, TaskResultContent] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.steps is None:
            self.steps = []
        if self.task_results is None:
            self.task_results = {}

    @property
    def step_ids(self) -> List[str]:
        """拥有的 step 的 id 列表"""
        return [s.id for s in self.steps]


@dataclass
class WorkflowResult:
    """Workflow 整体执行结果"""
    workflow_id: str = ""
    success: bool = False
    step_results: List[StepResult] = field(default_factory=list)
    error: Optional[str] = None
