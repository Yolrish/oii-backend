"""
API v1 路由聚合
将所有 v1 版本的端点路由聚合到一个 router 中
"""
from fastapi import APIRouter

from api.v1.endpoints import health, users, items

# 创建 v1 版本的主路由
api_router = APIRouter()

# 注册各个子路由
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(items.router)

