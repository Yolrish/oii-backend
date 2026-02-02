"""
OpenSearch 客户端模块

封装与 OpenSearch 集群的底层交互
"""

from typing import Optional, List, Dict, Any, Tuple
import warnings

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from .config import OpenSearchConfig, INDEX_MAPPING


class OpenSearchClient:
    """OpenSearch 客户端封装"""
    
    def __init__(self, config: Optional[OpenSearchConfig] = None):
        self.config = config or OpenSearchConfig()
        self._client: Optional[OpenSearch] = None
    
    @property
    def client(self) -> OpenSearch:
        """懒加载获取客户端"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> OpenSearch:
        """创建 OpenSearch 客户端"""
        if not self.config.verify_certs:
            warnings.filterwarnings("ignore", message=".*verify_certs.*")
            warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")
        
        # 解析 host 和 url_prefix
        client_params = {
            "http_auth": (self.config.username, self.config.password),
            "use_ssl": self.config.use_ssl,
            "verify_certs": self.config.verify_certs,
        }
        
        host = self.config.host
        if "://" in host:
            protocol, rest = host.split("://", 1)
            if "/" in rest:
                host_port, url_prefix = rest.split("/", 1)
                client_params["hosts"] = [f"{protocol}://{host_port}"]
                client_params["url_prefix"] = f"/{url_prefix}"
            else:
                client_params["hosts"] = [host]
        else:
            client_params["hosts"] = [host]
        
        return OpenSearch(**client_params)
    
    def ping(self) -> bool:
        """测试连接"""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息"""
        try:
            return self.client.info()
        except Exception:
            return {}
    
    def index_exists(self, index_name: Optional[str] = None) -> bool:
        """检查索引是否存在"""
        index_name = index_name or self.config.index_name
        return self.client.indices.exists(index=index_name)
    
    def create_index(self, index_name: Optional[str] = None, force: bool = False) -> bool:
        """
        创建索引
        
        Args:
            index_name: 索引名称
            force: 是否强制重建（删除已有索引后重新创建）
        Returns:
            True 表示索引可用（已存在或新建成功）
        """
        index_name = index_name or self.config.index_name
        
        if self.index_exists(index_name):
            if force:
                # 强制模式：删除后重建
                print(f"索引 '{index_name}' 已存在，强制删除重建")
                self.delete_index(index_name)
            else:
                # 非强制模式：继续使用已有索引
                print(f"索引 '{index_name}' 已存在，继续使用")
                return True
        
        body = {
            "settings": {
                "number_of_shards": self.config.number_of_shards,
                "number_of_replicas": self.config.number_of_replicas,
            },
            "mappings": INDEX_MAPPING,
        }
        
        try:
            self.client.indices.create(index=index_name, body=body)
            print(f"索引 '{index_name}' 创建成功")
            return True
        except Exception as e:
            print(f"创建索引失败: {e}")
            return False
    
    def delete_index(self, index_name: Optional[str] = None) -> bool:
        """删除索引"""
        index_name = index_name or self.config.index_name
        if not self.index_exists(index_name):
            return False
        try:
            self.client.indices.delete(index=index_name)
            return True
        except Exception:
            return False
    
    def index_document(self, document: Dict[str, Any], index_name: Optional[str] = None) -> Dict[str, Any]:
        """写入单个文档"""
        index_name = index_name or self.config.index_name
        try:
            return self.client.index(index=index_name, body=document)
        except Exception as e:
            return {"error": str(e)}
    
    def bulk_index(self, documents: List[Dict[str, Any]], index_name: Optional[str] = None) -> Tuple[int, int]:
        """批量写入文档"""
        index_name = index_name or self.config.index_name
        actions = [{"_index": index_name, "_source": doc} for doc in documents]
        
        try:
            success, failed = bulk(
                self.client,
                actions,
                stats_only=True,
                chunk_size=self.config.bulk_size,
            )
            return success, failed
        except Exception:
            return 0, len(documents)
    
    def close(self) -> None:
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None

