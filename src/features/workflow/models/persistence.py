"""
Handler 路径解析：字符串 → callable

Task 执行时由 Service 调用 resolve_handler(handler_path) 得到可执行函数。
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
