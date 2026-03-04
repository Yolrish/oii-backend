"""
工具注册表

所有工具统一通过 register_tool 注册。
模块职责：注册、列出、执行。不关心工具来源。
"""

from typing import Callable, Dict, Any, List, Optional
import asyncio
import inspect


# name -> (OpenAI 格式定义, handler)
_tools: Dict[str, tuple] = {}


def register_tool(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    required: Optional[List[str]] = None,
):
    """
    注册函数为可调用的工具

    Args:
        name: 工具名称（唯一）
        description: 工具描述，供 LLM 理解用途
        parameters: JSON Schema 的 properties
        required: 必填参数列表
    """

    def decorator(fn: Callable) -> Callable:
        params = parameters or {}
        req = list(required or [])
        if not req and params:
            for pname, pdef in params.items():
                if isinstance(pdef, dict) and pdef.get("default") is None:
                    req.append(pname)

        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": req,
                },
            },
        }
        _tools[name] = (tool_def, fn)
        return fn

    return decorator


def get_tools_for_llm() -> List[dict]:
    """返回所有已注册工具的 OpenAI 格式列表"""
    return [t[0] for t in _tools.values()]


def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """同步执行工具"""
    if name not in _tools:
        raise ValueError(f"Unknown tool: {name}")
    _, fn = _tools[name]
    sig = inspect.signature(fn)
    valid = {k: v for k, v in arguments.items() if k in sig.parameters}
    return fn(**valid)


async def execute_tool_async(name: str, arguments: Dict[str, Any]) -> Any:
    """执行工具（自动适配同步/异步 handler）"""
    if name not in _tools:
        raise ValueError(f"Unknown tool: {name}")
    _, fn = _tools[name]
    sig = inspect.signature(fn)
    valid = {k: v for k, v in arguments.items() if k in sig.parameters}
    if asyncio.iscoroutinefunction(fn):
        return await fn(**valid)
    return fn(**valid)


def unregister_tool(name: str) -> bool:
    """移除已注册的工具，返回是否成功"""
    return _tools.pop(name, None) is not None


def has_tool(name: str) -> bool:
    """检查工具是否已注册"""
    return name in _tools
