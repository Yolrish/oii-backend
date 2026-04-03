"""
API v1 路由聚合
将所有 v1 版本的端点路由聚合到一个 router 中
"""
from fastapi import APIRouter

from api.v1.endpoints import health
from features.chat.api import chat_router
from features.prompt.api import prompt_router
from features.auth.api import auth_router

# 创建 v1 版本的主路由
api_router = APIRouter()

# 注册各个子路由
api_router.include_router(health.router)
api_router.include_router(chat_router)
api_router.include_router(prompt_router)
api_router.include_router(auth_router)

# ==================== 已禁用的路由 ====================
# workflow：全部端点无认证，/run 可通过 shell handler 执行任意代码，暂时禁用
# from features.workflow import workflow_router
# api_router.include_router(workflow_router)
