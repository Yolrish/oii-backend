"""
Claude 对话模块

基于 Anthropic SDK 的对话服务，支持：
- 普通对话（单轮 / 多轮）
- Tool Calling（自动循环调用 tool_call 模块中注册的工具）
- 流式输出
"""

from .configs import ClaudeConfig, default_config
from .models.messages import Message, Role, ToolCall, ToolResult
from .providers.client import ClaudeClient
from .services.service import ClaudeService, create_claude_service

__all__ = [
    "ClaudeConfig",
    "default_config",
    "Message",
    "Role",
    "ToolCall",
    "ToolResult",
    "ClaudeClient",
    "ClaudeService",
    "create_claude_service",
]

__version__ = "1.0.0"
