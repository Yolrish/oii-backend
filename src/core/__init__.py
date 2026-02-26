"""
核心模块：配置、数据库连接等
"""
from core.config import MongoDBConfig
from core.mongodb import (
    get_database,
    connect_mongodb,
    close_mongodb,
)

__all__ = [
    "MongoDBConfig",
    "get_database",
    "connect_mongodb",
    "close_mongodb",
]
