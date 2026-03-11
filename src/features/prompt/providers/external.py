"""
外部 Prompt 提供者（预留）

用于对接第三方 prompt 平台。实现后注入 PromptService 即可。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models.models import PromptTemplate


class ExternalPromptProvider(ABC):
    """
    外部 prompt 来源接口

    实现此接口以对接第三方 prompt 管理平台。
    """

    @abstractmethod
    async def get_prompt(self, name: str) -> Optional[PromptTemplate]:
        """按名称获取"""

    @abstractmethod
    async def list_prompts(self, tag: Optional[str] = None) -> List[PromptTemplate]:
        """列出可用模板"""
