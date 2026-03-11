"""
Prompt 数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class PromptSource(str, Enum):
    """Prompt 来源"""
    BUILTIN = "builtin"    # 代码内置，不可通过 API 删改
    USER = "user"          # 用户创建，存 MongoDB
    EXTERNAL = "external"  # 第三方平台（预留）


@dataclass
class PromptVar:
    """模板变量定义"""

    name: str
    description: str = ""
    default: Optional[str] = None
    required: bool = False


@dataclass
class PromptTemplate:
    """
    Prompt 模板

    支持 {var_name} 变量替换。
    """

    name: str
    template: str
    description: str = ""
    source: str = PromptSource.USER
    variables: List[PromptVar] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    # DB 相关
    id: str = field(default_factory=lambda: f"prompt_{uuid.uuid4().hex[:12]}")
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = field(default_factory=datetime.utcnow)

    def render(self, **kwargs: Any) -> str:
        """渲染模板，将变量替换为实际值"""
        values = {}
        for var in self.variables:
            if var.name in kwargs:
                values[var.name] = kwargs[var.name]
            elif var.default is not None:
                values[var.name] = var.default
            elif var.required:
                raise ValueError(f"Prompt '{self.name}' 缺少必填变量: {var.name}")
        for k, v in kwargs.items():
            if k not in values:
                values[k] = v
        return self.template.format(**values)

    def get_variable_names(self) -> List[str]:
        return [v.name for v in self.variables]
