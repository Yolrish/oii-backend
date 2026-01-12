"""
Log 日志服务包

这是一个支持多 Provider 的日志写入服务：
- 统一的 LogService 入口
- 可扩展的 Provider 架构（OpenSearch、Elasticsearch、File 等）
- 单例模式
- 支持单条和批量写入

使用示例：
    from log import LogService, OpenSearchProvider
    
    # 获取服务并注册 Provider
    service = LogService()
    service.register_provider(OpenSearchProvider())
    service.init()
    
    # 写入日志（发送到所有已注册的 Provider）
    service.info("User logged in", service="auth")
    
    # 指定特定 Provider
    service.error("Error", service="api", providers=["opensearch"])

快捷方式：
    from log import create_default_log_service
    
    service = create_default_log_service()  # 自动注册 OpenSearch
    service.init()
    service.info("Hello")
"""

# 核心类
from .configs.config import LogServiceConfig
from .models.models import LogLevel, LogEntry
from .providers.base import BaseLogProvider
from .services.service import LogService, get_log_service, create_default_log_service

# Providers
from .providers import OpenSearchProvider, OpenSearchConfig

__all__ = [
    # 配置
    "LogServiceConfig",
    "LogLevel",
    "LogEntry",
    # 核心
    "BaseLogProvider",
    "LogService",
    "get_log_service",
    "create_default_log_service",
    # Providers
    "OpenSearchProvider",
    "OpenSearchConfig",
]

__version__ = "2.0.0"
