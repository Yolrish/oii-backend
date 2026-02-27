"""
LogService 模块

统一的日志服务入口，整合多个日志 Provider，支持 Web 后端高并发场景
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Tuple

from ..configs.config import LogServiceConfig
from ..models.models import LogEntry, LogLevel
from ..providers.base import BaseLogProvider
from ..providers import OpenSearchProvider, OpenSearchConfig


class LogService:
    """
    统一日志服务（单例模式，线程安全）
    
    整合多个日志 Provider，支持高并发场景。
    
    特性：
    - 线程安全：写入操作使用锁保护
    - 异步支持：提供 async 版本方法
    - 批量写入：支持批量日志写入
    
    使用示例：
        # 同步使用
        service = LogService()
        service.register_provider(OpenSearchProvider())
        service.init()
        service.info("Hello", service="api")
        
        # 异步使用（FastAPI）
        await service.info_async("Hello", service="api")
    """
    
    _instance: Optional["LogService"] = None
    _initialized: bool = False
    _lock = threading.Lock()  # 类级别锁，保护单例创建
    
    def __new__(cls, config: Optional[LogServiceConfig] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[LogServiceConfig] = None):
        with LogService._lock:
            if LogService._initialized:
                return
            
            self.config = config or LogServiceConfig()
            self._providers: Dict[str, BaseLogProvider] = {}
            self._write_lock = threading.Lock()  # 实例级别锁，保护写入操作
            self._thread_pool = ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="log_"
            )
            LogService._initialized = True
    
    @classmethod
    def get_instance(cls, config: Optional[LogServiceConfig] = None) -> "LogService":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None
            cls._initialized = False
    
    # ==================== Provider 管理 ====================
    
    def register_provider(self, provider: BaseLogProvider) -> "LogService":
        """
        注册日志 Provider
        
        Args:
            provider: Provider 实例
        Returns:
            self（支持链式调用）
        """
        with self._write_lock:
            self._providers[provider.name] = provider
        return self
    
    def unregister_provider(self, name: str) -> bool:
        """
        注销日志 Provider
        
        Args:
            name: Provider 名称
        Returns:
            是否成功
        """
        with self._write_lock:
            if name in self._providers:
                self._providers[name].close()
                del self._providers[name]
                return True
        return False
    
    def get_provider(self, name: str) -> Optional[BaseLogProvider]:
        """获取指定 Provider"""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """列出所有已注册的 Provider 名称"""
        return list(self._providers.keys())
    
    def _get_target_providers(self, providers: Optional[List[str]] = None) -> List[BaseLogProvider]:
        """
        获取目标 Provider 列表
        
        Args:
            providers: 指定的 Provider 名称列表，为 None 时使用默认配置
        Returns:
            Provider 实例列表
        """
        names = providers or self.config.default_providers
        return [self._providers[n] for n in names if n in self._providers]
    
    # ==================== 初始化 ====================
    
    def init(self, force: bool = False, providers: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        初始化 Provider
        
        Args:
            force: 是否强制重新初始化
            providers: 指定初始化哪些 Provider，为 None 时初始化所有
        Returns:
            各 Provider 初始化结果
        """
        targets = self._get_target_providers(providers) if providers else list(self._providers.values())
        return {p.name: p.init(force=force) for p in targets}
    
    def is_ready(self, providers: Optional[List[str]] = None) -> Dict[str, bool]:
        """检查各 Provider 是否就绪"""
        targets = self._get_target_providers(providers) if providers else list(self._providers.values())
        return {p.name: p.is_ready() for p in targets}
    
    # ==================== 同步日志写入 ====================
    
    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.LOG,
        service: str = "default",
        providers: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Optional[str]]:
        """
        写入单条日志（同步）
        
        Args:
            message: 日志消息
            level: 日志级别
            service: 服务类别
            providers: 指定使用哪些 Provider，为 None 时使用默认配置
            **kwargs: 其他可选参数
        Returns:
            各 Provider 的写入结果（文档 ID 或 None）
        """
        entry = LogEntry(message=message, level=level, service=service, **kwargs)
        targets = self._get_target_providers(providers)
        
        results = {}
        with self._write_lock:
            for provider in targets:
                try:
                    results[provider.name] = provider.write(entry)
                except Exception as e:
                    if not self.config.fail_silently:
                        raise
                    results[provider.name] = None
                    print(f"[{provider.name}] 写入失败: {e}")
        
        return results
    
    def info(self, message: str, service: str = "default", **kwargs) -> Dict[str, Optional[str]]:
        """写入普通日志（同步）"""
        return self.log(message, LogLevel.LOG, service, **kwargs)
    
    def warn(self, message: str, service: str = "default", **kwargs) -> Dict[str, Optional[str]]:
        """写入警告日志（同步）"""
        return self.log(message, LogLevel.WARN, service, **kwargs)
    
    def error(self, message: str, service: str = "default", **kwargs) -> Dict[str, Optional[str]]:
        """写入错误日志（同步）"""
        return self.log(message, LogLevel.ERROR, service, **kwargs)
    
    def bulk_log(
        self,
        entries: List[LogEntry],
        providers: Optional[List[str]] = None
    ) -> Dict[str, Tuple[int, int]]:
        """
        批量写入日志（同步）
        
        Args:
            entries: 日志条目列表
            providers: 指定使用哪些 Provider
        Returns:
            各 Provider 的写入结果 {name: (成功数, 失败数)}
        """
        targets = self._get_target_providers(providers)
        
        results = {}
        with self._write_lock:
            for provider in targets:
                try:
                    results[provider.name] = provider.bulk_write(entries)
                except Exception as e:
                    if not self.config.fail_silently:
                        raise
                    results[provider.name] = (0, len(entries))
                    print(f"[{provider.name}] 批量写入失败: {e}")
        
        return results
    
    # ==================== 异步日志写入（推荐在 Web 后端使用）====================
    
    async def log_async(
        self,
        message: str,
        level: LogLevel = LogLevel.LOG,
        service: str = "default",
        providers: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Optional[str]]:
        """
        写入单条日志（异步）
        
        Args:
            message: 日志消息
            level: 日志级别
            service: 服务类别
            providers: 指定使用哪些 Provider
            **kwargs: 其他可选参数
        Returns:
            各 Provider 的写入结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool,
            lambda: self.log(message, level, service, providers, **kwargs)
        )
    
    async def info_async(self, message: str, service: str = "default", **kwargs) -> Dict[str, Optional[str]]:
        """写入普通日志（异步）"""
        return await self.log_async(message, LogLevel.LOG, service, **kwargs)
    
    async def warn_async(self, message: str, service: str = "default", **kwargs) -> Dict[str, Optional[str]]:
        """写入警告日志（异步）"""
        return await self.log_async(message, LogLevel.WARN, service, **kwargs)
    
    async def error_async(self, message: str, service: str = "default", **kwargs) -> Dict[str, Optional[str]]:
        """写入错误日志（异步）"""
        return await self.log_async(message, LogLevel.ERROR, service, **kwargs)
    
    async def bulk_log_async(
        self,
        entries: List[LogEntry],
        providers: Optional[List[str]] = None
    ) -> Dict[str, Tuple[int, int]]:
        """
        批量写入日志（异步）
        
        Args:
            entries: 日志条目列表
            providers: 指定使用哪些 Provider
        Returns:
            各 Provider 的写入结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool,
            lambda: self.bulk_log(entries, providers)
        )
    
    # ==================== 生命周期 ====================
    
    def close(self) -> None:
        """关闭所有 Provider 和线程池"""
        with self._write_lock:
            for provider in self._providers.values():
                provider.close()
            self._providers.clear()
        self._thread_pool.shutdown(wait=False)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass  # 单例模式下不关闭
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass  # 单例模式下不关闭


def get_log_service(config: Optional[LogServiceConfig] = None) -> LogService:
    """获取日志服务单例"""
    return LogService.get_instance(config)


# ==================== 快捷函数：自动注册 OpenSearch ====================

def create_default_log_service(
    opensearch_config: Optional[OpenSearchConfig] = None,
    service_config: Optional[LogServiceConfig] = None
) -> LogService:
    """
    创建默认配置的日志服务（自动注册 OpenSearch）
    
    Args:
        opensearch_config: OpenSearch 配置
        service_config: LogService 配置
    Returns:
        配置好的 LogService 实例
    """
    service = LogService(service_config)
    service.register_provider(OpenSearchProvider(opensearch_config or OpenSearchConfig.from_env()))
    return service
