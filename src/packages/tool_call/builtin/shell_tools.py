"""
Shell 工具：将 Shell 模块能力暴露给 tool-call
"""

from ..registry import register_tool


@register_tool(
    name="run_shell_command",
    description="在服务器上执行 shell 命令，返回 stdout、stderr 和退出码。适用于查询系统状态、执行脚本等。",
    parameters={
        "command": {
            "type": "string",
            "description": "要执行的命令，如 ls -la、pwd、git status",
        },
        "timeout": {
            "type": "integer",
            "description": "超时秒数，默认 60",
        },
        "cwd": {
            "type": "string",
            "description": "工作目录，为空则使用当前目录",
        },
    },
    required=["command"],
)
def run_shell_command(
    command: str,
    timeout: int = 60,
    cwd: str = "",
) -> dict:
    """执行 shell 命令"""
    from packages.shell import create_shell_service

    svc = create_shell_service()
    result = svc.run(
        command,
        cwd=cwd if cwd else None,
        timeout=timeout,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "success": result.returncode == 0,
    }
