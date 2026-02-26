"""
MongoDB 连接管理
使用 Motor 异步驱动，在应用 lifespan 中建立与关闭连接。
Motor 基于 PyMongo，支持相同的 ServerApi 等参数，便于与官方推荐用法一致。
"""
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

from core.config import MongoDBConfig


# 全局客户端，由 lifespan 初始化与关闭
_client: Optional[AsyncIOMotorClient] = None
_db_name: str = "ai_backend"


async def connect_mongodb(config: Optional[MongoDBConfig] = None) -> AsyncIOMotorClient:
    """
    建立 MongoDB 连接，应在应用启动时调用。
    使用 ServerApi('1') 与官方推荐一致，连接 Atlas 时行为更稳定。
    """
    global _client, _db_name
    cfg = config or MongoDBConfig.from_env()
    _db_name = cfg.db_name
    _client = AsyncIOMotorClient(
        cfg.uri,
        server_api=ServerApi("1"),
        serverSelectionTimeoutMS=5000,
    )
    # 触发一次连接检查（与官方示例的 ping 一致）
    await _client.admin.command("ping")
    return _client


async def close_mongodb() -> None:
    """
    关闭 MongoDB 连接，应在应用关闭时调用
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    """
    获取当前默认数据库实例
    需在 connect_mongodb 之后调用，供 FastAPI 依赖注入使用
    """
    if _client is None:
        raise RuntimeError("MongoDB 未连接，请确保在 lifespan 中已调用 connect_mongodb")
    return _client[_db_name]


def get_client() -> Optional[AsyncIOMotorClient]:
    """获取当前 Motor 客户端（可选，用于多库或高级用法）"""
    return _client
