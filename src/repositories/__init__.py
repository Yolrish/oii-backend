"""
Repositories 模块
数据访问层，负责 CRUD 操作
"""
from repositories.base import BaseRepository, InMemoryRepository
from repositories.user_repo import UserRepository, user_repository
from repositories.item_repo import ItemRepository, item_repository

__all__ = [
    "BaseRepository",
    "InMemoryRepository",
    "UserRepository",
    "user_repository",
    "ItemRepository", 
    "item_repository",
]

