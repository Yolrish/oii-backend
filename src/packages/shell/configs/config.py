"""
Shell 模块配置
优先级：os.environ > shell 包 .env > 默认值
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict

from load_env import load_module_env

# 模块加载时补充 shell 包 .env（不覆盖已有变量）
load_module_env(__file__)


# 环境变量名称
ENV_SHELL_TIMEOUT = "SHELL_TIMEOUT"
ENV_SHELL_ENCODING = "SHELL_ENCODING"


def _get_default_encoding() -> str:
    """获取默认编码"""
    return os.environ.get(ENV_SHELL_ENCODING, "utf-8")


def _get_default_timeout() -> int:
    """获取默认超时时间"""
    return int(os.environ.get(ENV_SHELL_TIMEOUT, "300"))


def _get_default_shell() -> str:
    """获取默认 shell"""
    if sys.platform == "win32":
        return os.environ.get("COMSPEC", "cmd.exe")
    return os.environ.get("SHELL", "/bin/sh")


@dataclass
class ShellConfig:
    """Shell 执行器配置"""
    
    # 默认超时（秒），0 表示无限制
    timeout: int = field(default_factory=_get_default_timeout)
    
    # 输出编码
    encoding: str = field(default_factory=_get_default_encoding)
    
    # 默认工作目录（None 表示当前目录）
    cwd: Optional[str] = None
    
    # 默认环境变量（None 表示继承当前进程环境）
    env: Optional[Dict[str, str]] = None
    
    # 是否在执行失败时抛出异常
    raise_on_error: bool = False
    
    # 默认 shell 路径
    shell: str = field(default_factory=_get_default_shell)
    
    # 是否合并 stderr 到 stdout
    merge_stderr: bool = False


# 默认配置
default_config = ShellConfig()
