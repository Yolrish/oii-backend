"""
Tool-Call 模块

统一的工具注册与执行。所有工具均通过 register_tool 注册，
模块只关心「注册 + 列出 + 执行」，不关心工具来源。
"""

# 导入内置工具以触发注册
from .builtin import *  # noqa: F401, F403

from .registry import (
    register_tool,
    get_tools_for_llm,
    execute_tool,
    execute_tool_async,
    unregister_tool,
    has_tool,
)

__all__ = [
    "register_tool",
    "get_tools_for_llm",
    "execute_tool",
    "execute_tool_async",
    "unregister_tool",
    "has_tool",
]

__version__ = "1.0.0"
