"""
全局配置模块

定义 LogService 的全局配置
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class LogServiceConfig:
    """
    LogService 全局配置
    
    属性：
        default_providers: 默认启用的 Provider 名称列表
        fail_silently: 写入失败时是否静默（不抛异常）
    """
    default_providers: List[str] = field(default_factory=lambda: ["opensearch"])
    fail_silently: bool = True  # 生产环境建议开启，避免日志异常影响主业务

