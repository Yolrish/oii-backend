"""
日志 Provider 基类模块

定义所有日志工具必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

from ..models.models import LogEntry


class BaseLogProvider(ABC):
    """
    日志 Provider 抽象基类
    
    所有日志工具（OpenSearch、Elasticsearch、File 等）都必须继承此类并实现以下方法。
    这确保了 LogService 可以统一调用不同的日志工具。
    """
    
    # Provider 名称，用于标识和选择
    name: str = "base"
    
    @abstractmethod
    def init(self, force: bool = False) -> bool:
        """
        初始化 Provider（如创建索引、打开文件等）
        
        Args:
            force: 是否强制重新初始化
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """
        检查 Provider 是否就绪
        
        Returns:
            是否就绪
        """
        pass
    
    @abstractmethod
    def write(self, entry: LogEntry) -> Optional[str]:
        """
        写入单条日志
        
        Args:
            entry: 日志条目
        Returns:
            写入成功返回标识符（如文档 ID），失败返回 None
        """
        pass
    
    @abstractmethod
    def bulk_write(self, entries: List[LogEntry]) -> Tuple[int, int]:
        """
        批量写入日志
        
        Args:
            entries: 日志条目列表
        Returns:
            (成功数, 失败数)
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭 Provider，释放资源"""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"

