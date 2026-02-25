"""
Shell 命令执行模块

提供系统命令行执行能力，支持：
- 同步/异步执行
- 并发调用（无状态设计）
- 实时流式输出（回调模式 / 生成器模式）

使用示例：
    # 快捷方式
    from packages.shell import run, run_async
    
    result = run("git status")
    result = await run_async("git status")
    
    # 使用服务
    from packages.shell import create_shell_service
    
    service = create_shell_service()
    result = service.run("git status")
    
    # 实时输出
    result = service.run("pip install xxx", on_stdout=print)
    
    # 异步并发
    import asyncio
    results = await asyncio.gather(
        service.run_async("task1"),
        service.run_async("task2"),
    )
    
    # 生成器模式
    for line in service.stream("npm install"):
        print(f"[{line.stream_type}] {line.content}")
    
    # 自定义配置
    from packages.shell import ShellConfig, create_shell_service
    
    config = ShellConfig(timeout=600, raise_on_error=True)
    service = create_shell_service(config)
"""

# 配置
from .configs import ShellConfig, default_config

# 模型
from .models import CommandResult, StreamType, StreamLine

# 异常
from .providers.exceptions import ShellError, ShellTimeoutError, ShellExecutionError

# 执行器
from .providers import ShellExecutor

# 服务
from .services import (
    ShellService,
    get_default_service,
    create_shell_service,
    run,
    run_async,
)

__all__ = [
    # 配置
    "ShellConfig",
    "default_config",
    # 模型
    "CommandResult",
    "StreamType",
    "StreamLine",
    # 异常
    "ShellError",
    "ShellTimeoutError",
    "ShellExecutionError",
    # 执行器
    "ShellExecutor",
    # 服务
    "ShellService",
    "get_default_service",
    "create_shell_service",
    # 快捷函数
    "run",
    "run_async",
]

__version__ = "1.0.0"
