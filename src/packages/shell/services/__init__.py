"""
Shell 服务模块

支持 Web 后端高并发场景
"""
from .service import (
    ShellService,
    get_default_service,
    create_shell_service,
    run,
    run_async,
)

__all__ = [
    "ShellService",
    "get_default_service",
    "create_shell_service",
    "run",
    "run_async",
]
