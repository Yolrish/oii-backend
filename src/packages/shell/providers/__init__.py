"""
Shell 提供者模块

包含底层执行器和异常定义
"""
from .exceptions import ShellError, ShellTimeoutError, ShellExecutionError
from .executor import ShellExecutor

__all__ = [
    # 异常
    "ShellError",
    "ShellTimeoutError",
    "ShellExecutionError",
    # 执行器
    "ShellExecutor",
]
