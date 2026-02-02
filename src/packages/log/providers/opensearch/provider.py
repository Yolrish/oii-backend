"""
OpenSearch Provider 模块

实现 BaseLogProvider 接口，提供 OpenSearch 日志写入功能
"""

from typing import Optional, List, Tuple

from ..base import BaseLogProvider
from ...models.models import LogEntry
from .config import OpenSearchConfig
from .client import OpenSearchClient


class OpenSearchProvider(BaseLogProvider):
    """
    OpenSearch 日志 Provider
    
    实现基于 OpenSearch 的日志写入功能
    """
    
    name = "opensearch"
    
    def __init__(self, config: Optional[OpenSearchConfig] = None):
        """
        初始化 Provider
        
        Args:
            config: OpenSearch 配置，为 None 时使用默认配置
        """
        self.config = config or OpenSearchConfig()
        self._client = OpenSearchClient(self.config)
    
    def init(self, force: bool = False) -> bool:
        """初始化索引"""
        if not self._client.ping():
            print(f"[{self.name}] 无法连接到 OpenSearch")
            return False
        return self._client.create_index(force=force)
    
    def is_ready(self) -> bool:
        """检查是否就绪"""
        return self._client.ping() and self._client.index_exists()
    
    def write(self, entry: LogEntry) -> Optional[str]:
        """写入单条日志（支持指定 index）"""
        # 使用 entry.index 或默认配置的 index_name
        index_name = entry.index or self.config.index_name
        result = self._client.index_document(entry.to_dict(), index_name=index_name)
        return result.get("_id")
    
    def bulk_write(self, entries: List[LogEntry]) -> Tuple[int, int]:
        """批量写入日志（按 index 分组写入）"""
        # 按 index 分组
        grouped: dict[str, list] = {}
        for entry in entries:
            index_name = entry.index or self.config.index_name
            if index_name not in grouped:
                grouped[index_name] = []
            grouped[index_name].append(entry.to_dict())
        
        # 分组批量写入
        total_success = 0
        total_failed = 0
        for index_name, documents in grouped.items():
            success, failed = self._client.bulk_index(documents, index_name=index_name)
            total_success += success
            total_failed += failed
        
        return total_success, total_failed
    
    def init_index(self, index_name: str, force: bool = False) -> bool:
        """初始化指定索引（用于多索引场景）"""
        return self._client.create_index(index_name=index_name, force=force)
    
    def close(self) -> None:
        """关闭连接"""
        self._client.close()
    
    def get_cluster_name(self) -> str:
        """获取集群名称（OpenSearch 特有方法）"""
        return self._client.get_cluster_info().get("cluster_name", "unknown")

