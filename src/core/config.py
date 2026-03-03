"""
MongoDB 配置
优先级：os.environ > core 包 .env > 默认值
"""
import os
from dataclasses import dataclass

from load_env import load_module_env


@dataclass
class MongoDBConfig:
    """
    MongoDB 连接配置
    """
    # 连接 URI，例如: mongodb://localhost:27017 或 mongodb+srv://user:pass@cluster.mongodb.net
    uri: str = "mongodb://localhost:27017"
    # 默认数据库名
    db_name: str = "ai_backend"

    @classmethod
    def from_env(cls) -> "MongoDBConfig":
        """从环境变量加载配置（优先内存，其次 core/.env，最后默认值）"""
        load_module_env(__file__)
        return cls(
            uri=os.getenv("MONGO_DATABASE_URL", cls.uri),
            db_name=os.getenv("MONGO_DATABASE_NAME", cls.db_name),
        )
