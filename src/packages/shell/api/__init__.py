"""
Shell API 子包（仅 Controller util，无 Router / 不暴露 Web）
"""

from .controller import run_command, run_command_task

__all__ = [
    "run_command",
    "run_command_task",
]
