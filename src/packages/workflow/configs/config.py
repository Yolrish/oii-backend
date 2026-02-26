"""
Workflow 运行与持久化配置
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkflowConfig:
    """
    工作流执行与持久化配置
    """
    # ---------- 执行 ----------
    # 单个 step 超时（秒），0 表示不限制
    step_timeout: float = 0.0
    # 单个 task 超时（秒），0 表示不限制
    task_timeout: float = 0.0
    # step 内 task 并发上限，0 表示不限制（全部并行）
    max_task_concurrent: int = 0

    # ---------- 持久化（数据库） ----------
    # 是否启用持久化（需在创建 WorkflowService 时注入 db 实例）
    persist_enabled: bool = False
    # 存储 workflow 的集合名（MongoDB collection）
    collection_name: str = "workflows"

    @classmethod
    def from_env(cls) -> "WorkflowConfig":
        """从环境变量加载配置"""
        persist = os.getenv("WORKFLOW_PERSIST_ENABLED", "").lower() in ("1", "true", "yes")
        return cls(
            step_timeout=float(os.getenv("WORKFLOW_STEP_TIMEOUT", cls.step_timeout)),
            task_timeout=float(os.getenv("WORKFLOW_TASK_TIMEOUT", cls.task_timeout)),
            max_task_concurrent=int(os.getenv("WORKFLOW_MAX_TASK_CONCURRENT", cls.max_task_concurrent)),
            persist_enabled=persist,
            collection_name=os.getenv("WORKFLOW_COLLECTION_NAME", cls.collection_name),
        )


default_config = WorkflowConfig()
