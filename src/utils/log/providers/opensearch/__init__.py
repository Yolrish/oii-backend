"""
OpenSearch 日志工具包

提供 OpenSearch 日志写入功能
"""

from .config import OpenSearchConfig
from .provider import OpenSearchProvider

__all__ = [
    "OpenSearchConfig",
    "OpenSearchProvider",
]

