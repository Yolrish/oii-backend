"""
Chat 数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


def _new_session_id() -> str:
    return f"session_{uuid.uuid4().hex[:12]}"


def _new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


@dataclass
class Session:
    """会话元数据"""

    id: str = field(default_factory=_new_session_id)
    user_id: str = ""
    title: str = ""
    system_prompt: str = ""
    use_tools: bool = False
    status: str = SessionStatus.ACTIVE
    message_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """单条对话消息"""

    id: str = field(default_factory=_new_message_id)
    session_id: str = ""
    role: str = "user"  # user | assistant
    content: str = ""
    # Anthropic 原始 content blocks（含 tool_use 等），用于回传给 API
    raw_content: Optional[List[Any]] = None
    # 本条消息中的工具调用记录
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    # token 消耗（估算）
    token_count: int = 0
    # 消息序号，用于排序
    seq: int = 0
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
