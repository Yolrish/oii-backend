"""
Prompt 配置
"""

import os
from dataclasses import dataclass

from load_env import load_module_env


@dataclass
class PromptConfig:
    """Prompt 模块配置"""

    collection: str = "prompts"

    @classmethod
    def from_env(cls) -> "PromptConfig":
        load_module_env(__file__)
        return cls(
            collection=os.getenv("PROMPT_COLLECTION", cls.collection),
        )


default_config = PromptConfig()
