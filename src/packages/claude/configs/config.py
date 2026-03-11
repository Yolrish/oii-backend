"""
Claude 配置
优先级：os.environ > claude 包 .env > 默认值
"""

import os
from dataclasses import dataclass
from typing import Optional

from load_env import load_module_env


@dataclass
class ClaudeConfig:
    """Claude API 配置"""

    api_key: str = ""
    # 模型名称
    model: str = "claude-sonnet-4-20250514"
    # 最大输出 token 数
    max_tokens: int = 4096
    # 温度
    temperature: float = 0.7
    # 系统提示词
    system_prompt: str = ""
    # tool calling 最大循环轮数
    max_tool_rounds: int = 10
    # 请求超时（秒）
    timeout: float = 120.0
    # 自定义 base_url（代理等场景）
    base_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ClaudeConfig":
        """从环境变量加载配置"""
        load_module_env(__file__)
        return cls(
            api_key=os.getenv("CLAUDE_API_KEY", cls.api_key),
            model=os.getenv("CLAUDE_MODEL", cls.model),
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", str(cls.max_tokens))),
            temperature=float(os.getenv("CLAUDE_TEMPERATURE", str(cls.temperature))),
            system_prompt=os.getenv("CLAUDE_SYSTEM_PROMPT", cls.system_prompt),
            max_tool_rounds=int(os.getenv("CLAUDE_MAX_TOOL_ROUNDS", str(cls.max_tool_rounds))),
            timeout=float(os.getenv("CLAUDE_TIMEOUT", str(cls.timeout))),
            base_url=os.getenv("CLAUDE_BASE_URL") or cls.base_url,
        )


default_config = ClaudeConfig()
