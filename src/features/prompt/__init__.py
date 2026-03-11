"""
Prompt 管理模块

多来源统一管理：builtin（代码内置）+ user（MongoDB）+ external（第三方预留）
"""

from .configs import PromptConfig, default_config
from .models import PromptTemplate, PromptVar, PromptSource
from .services import PromptService, create_prompt_service

__all__ = [
    "PromptConfig",
    "default_config",
    "PromptTemplate",
    "PromptVar",
    "PromptSource",
    "PromptService",
    "create_prompt_service",
]

__version__ = "1.0.0"
