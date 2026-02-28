"""
Shell 命令执行模块

在部署服务器本地执行系统命令；支持同步/异步、并发控制、实时输出与 stdin_input 预写。
结构见 README「模块结构」：configs / models / providers / services；无 api 层，不向 Web 暴露接口。
"""

# 配置
from .configs import ShellConfig, default_config

# 模型
from .models import CommandResult, StreamType, StreamLine

# 执行器与异常（providers）
from .providers import (
    ShellExecutor,
    ShellError,
    ShellTimeoutError,
    ShellExecutionError,
)

# 服务层
from .services import (
    ShellService,
    get_default_service,
    create_shell_service,
    run,
    run_async,
)

# API Controller（仅 util，无 Router，供内部调用）
from .api import run_command, run_command_task

__all__ = [
    # configs
    "ShellConfig",
    "default_config",
    # models
    "CommandResult",
    "StreamType",
    "StreamLine",
    # providers
    "ShellError",
    "ShellTimeoutError",
    "ShellExecutionError",
    "ShellExecutor",
    # services
    "ShellService",
    "get_default_service",
    "create_shell_service",
    "run",
    "run_async",
    # api controller util
    "run_command",
    "run_command_task",
]

__version__ = "1.0.0"
