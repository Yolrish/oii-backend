"""
OpenSearch 配置模块
优先级：os.environ > log 包 .env > 默认值
"""

from dataclasses import dataclass
import os
from typing import Dict, Any

from load_env import load_module_env


@dataclass
class OpenSearchConfig:
    """
    OpenSearch 配置类
    """
    # 连接配置
    host: str = "https://log.reelnova.ai/opensearch"
    username: str = "admin"
    password: str = "Account@Tapi.123"
    use_ssl: bool = True
    verify_certs: bool = True
    
    # 索引配置
    index_name: str = "logs-test"
    number_of_shards: int = 1
    number_of_replicas: int = 0
    
    # 写入配置
    bulk_size: int = 500
    
    @classmethod
    def from_env(cls) -> "OpenSearchConfig":
        """从环境变量加载配置（优先内存，其次 log/.env，最后默认值）"""
        load_module_env(__file__)
        return cls(
            host=os.getenv("OPENSEARCH_HOST", cls.host),
            username=os.getenv("OPENSEARCH_USERNAME", cls.username),
            password=os.getenv("OPENSEARCH_PASSWORD", cls.password),
            use_ssl=os.getenv("OPENSEARCH_USE_SSL", "true").lower() == "true",
            verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "true").lower() == "true",
            index_name=os.getenv("OPENSEARCH_INDEX_NAME", cls.index_name),
        )


# OpenSearch 索引字段映射
INDEX_MAPPING: Dict[str, Any] = {
    "properties": {
        "timestamp": {"type": "date"},
        "message": {"type": "text"},
        "level": {"type": "keyword"},
        "service": {"type": "keyword"},
        "user": {"type": "keyword"},
        "user_id": {"type": "keyword"},
        "status_code": {"type": "integer"},
        "ip": {"type": "ip"},
        "metadata": {"type": "object", "enabled": True},
    }
}

