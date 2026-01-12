"""
API v1 版本的依赖注入
"""
from typing import Optional

from fastapi import Header, HTTPException, status, Depends

from services.user_service import UserService, user_service
from services.item_service import ItemService, item_service
from schemas.common import PaginationParams


# ============ 认证依赖 ============

async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, description="用户ID")
) -> Optional[str]:
    """
    从请求头获取当前用户ID
    实际项目中这里会验证 JWT Token
    """
    return x_user_id


async def require_auth(
    x_user_id: Optional[str] = Header(None, description="用户ID")
) -> str:
    """
    要求用户必须登录
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return x_user_id


# ============ 分页依赖 ============

def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> PaginationParams:
    """
    通用分页参数
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    return PaginationParams(page=page, page_size=page_size)


# ============ Service 依赖 ============

def get_user_service() -> UserService:
    """
    获取用户服务实例
    实际项目中可以在这里注入数据库 session
    """
    return user_service


def get_item_service() -> ItemService:
    """
    获取物品服务实例
    """
    return item_service
