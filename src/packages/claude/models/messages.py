"""
消息模型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ToolCall:
    """LLM 返回的工具调用请求"""

    id: str
    name: str
    input: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果，回传给 LLM"""

    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """对话消息"""

    role: Role
    content: str = ""
    # 若 role=assistant 且 LLM 请求了工具调用
    tool_calls: List[ToolCall] = field(default_factory=list)
    # 若本条消息是工具结果
    tool_results: List[ToolResult] = field(default_factory=list)


@dataclass
class ChatResponse:
    """对话响应"""

    # 最终回复文本
    content: str = ""
    # 本次对话中触发的工具调用记录
    tool_calls_history: List[ToolCall] = field(default_factory=list)
    # 停止原因：end_turn | max_tool_rounds | error
    stop_reason: str = "end_turn"
    # 消耗的 token
    input_tokens: int = 0
    output_tokens: int = 0
