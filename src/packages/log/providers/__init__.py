"""
日志 Provider 集合

包含所有可用的日志工具实现
"""

from .opensearch import OpenSearchProvider, OpenSearchConfig

__all__ = [
    "OpenSearchProvider",
    "OpenSearchConfig",
]

