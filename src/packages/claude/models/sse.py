"""
SSE 事件格式规范

所有 SSE 事件统一使用 JSON 格式，通过 event 字段区分类型。
前端通过 EventSource 或 fetch + ReadableStream 消费。

事件类型：
  message_start    — 对话开始，包含 session/message 元信息
  content_delta    — 文本增量片段（逐 token）
  tool_use_start   — 开始调用工具
  tool_use_result  — 工具执行完毕，返回结果
  message_end      — 对话结束，包含 token 统计
  error            — 出错

SSE 格式示例：
  event: content_delta
  data: {"text": "你好"}

  event: tool_use_start
  data: {"tool_call_id": "toolu_xxx", "name": "run_shell_command", "input": {"command": "ls"}}

  event: tool_use_result
  data: {"tool_call_id": "toolu_xxx", "name": "run_shell_command", "result": {...}, "is_error": false}

  event: message_end
  data: {"stop_reason": "end_turn", "input_tokens": 120, "output_tokens": 350}
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


# SSE 事件类型常量
EVENT_MESSAGE_START = "message_start"
EVENT_CONTENT_DELTA = "content_delta"
EVENT_TOOL_USE_START = "tool_use_start"
EVENT_TOOL_USE_RESULT = "tool_use_result"
EVENT_MESSAGE_END = "message_end"
EVENT_ERROR = "error"


@dataclass
class SSEEvent:
    """SSE 事件基类"""

    event: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """序列化为 SSE 文本格式"""
        payload = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.event}\ndata: {payload}\n\n"


def sse_message_start(session_id: str = "", message_id: str = "") -> str:
    return SSEEvent(
        event=EVENT_MESSAGE_START,
        data={"session_id": session_id, "message_id": message_id},
    ).to_sse()


def sse_content_delta(text: str) -> str:
    return SSEEvent(
        event=EVENT_CONTENT_DELTA,
        data={"text": text},
    ).to_sse()


def sse_tool_use_start(
    tool_call_id: str, name: str, input_data: Dict[str, Any],
) -> str:
    return SSEEvent(
        event=EVENT_TOOL_USE_START,
        data={"tool_call_id": tool_call_id, "name": name, "input": input_data},
    ).to_sse()


def sse_tool_use_result(
    tool_call_id: str, name: str, result: Any, is_error: bool = False,
) -> str:
    return SSEEvent(
        event=EVENT_TOOL_USE_RESULT,
        data={
            "tool_call_id": tool_call_id,
            "name": name,
            "result": result,
            "is_error": is_error,
        },
    ).to_sse()


def sse_message_end(
    stop_reason: str = "end_turn",
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> str:
    return SSEEvent(
        event=EVENT_MESSAGE_END,
        data={
            "stop_reason": stop_reason,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    ).to_sse()


def sse_error(message: str, code: str = "internal_error") -> str:
    return SSEEvent(
        event=EVENT_ERROR,
        data={"message": message, "code": code},
    ).to_sse()
