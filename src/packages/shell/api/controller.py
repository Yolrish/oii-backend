"""
Shell API Controller 层（util 函数，非类）

供内部调用的入口：run_command(service, ...) 通用；run_command_task(context, **params) 专供 Workflow。
不暴露 Web API，无 Router。
"""
from typing import Any, Dict, Optional

from ..services import ShellService, get_default_service


def run_command(
    service: ShellService,
    command: str = "",
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    **kwargs: Any,
) -> Dict[str, str]:
    """
    执行一条 shell 命令，返回 { type, content }（内部直接调用，可传入指定 Service）。

    Args:
        service: ShellService 实例
        command: 要执行的命令
        cwd: 工作目录
        timeout: 超时秒数
        **kwargs: 其它参数传给 service.run（如 on_stdout、on_stderr、stdin_input）

    Returns:
        {"type": "text", "content": "stdout + stderr 或错误信息"}
    """
    if not command or not command.strip():
        return {"type": "text", "content": "No command provided."}
    allowed = ("on_stdout", "on_stderr", "stdin_input", "env")
    run_kw = {k: v for k, v in kwargs.items() if k in allowed}
    result = service.run(
        command.strip(),
        cwd=cwd,
        timeout=timeout,
        **run_kw,
    )
    content = result.stdout or ""
    if result.stderr:
        content = f"{content}\n{result.stderr}".strip() if content else result.stderr
    if not content:
        content = f"return_code={result.return_code}, success={result.success}"
    return {"type": "text", "content": content}


def run_command_task(
    context: Dict[str, Any],
    command: str = "",
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    service: Optional[ShellService] = None,
    **kwargs: Any,
) -> Dict[str, str]:
    """
    Workflow Task 用：签名为 (context, **params)，内部调用 run_command。
    handler_path 可设为 "packages.shell.api.controller.run_command_task"。
    未传入 service 时使用 get_default_service()，传入则使用指定实例（便于测试或自定义）。
    """
    svc = service if service is not None else get_default_service()
    return run_command(
        svc,
        command=command,
        cwd=cwd,
        timeout=timeout,
        **kwargs,
    )
