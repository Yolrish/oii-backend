"""
API v1 版本的依赖注入
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from schemas.common import PaginationParams
from core.mongodb import get_database


# ============ 分页依赖 ============

def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> PaginationParams:
    """通用分页参数"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    return PaginationParams(page=page, page_size=page_size)


# ============ MongoDB 依赖 ============

def get_mongo_db() -> AsyncIOMotorDatabase:
    """获取 MongoDB 数据库实例，用于路由中注入"""
    return get_database()
