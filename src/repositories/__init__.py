"""
Repositories 模块
数据访问层，负责 CRUD 操作
"""
from repositories.base import BaseRepository, InMemoryRepository

__all__ = [
    "BaseRepository",
    "InMemoryRepository",
]

