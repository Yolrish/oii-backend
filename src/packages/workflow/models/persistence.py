"""
持久化辅助：根据模块路径解析要执行的函数

供 ai_spec 等模块在从 Spec 加载 Workflow 时，将 handler 路径解析为 callable。
"""

from typing import Any, Callable, Optional
import importlib


def resolve_handler(handler_path: str) -> Optional[Callable[..., Any]]:
    """
    根据模块路径字符串解析出要执行的函数。
    格式：模块路径.函数名，如 "myapp.tasks.send_email"。
    """
    if not handler_path or "." not in handler_path:
        return None
    try:
        module_path, name = handler_path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, name, None)
    except (ImportError, AttributeError):
        return None
