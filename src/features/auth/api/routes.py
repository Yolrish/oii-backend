"""
Auth HTTP API
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from core.mongodb import get_database
from ..models.models import User, UserRole
from ..services.service import UserService, create_user_service
from .deps import get_current_user, require_admin

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


def _get_user_service() -> UserService:
    db = get_database()
    return create_user_service(db)


# ==================== 请求/响应模型 ====================


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


# ==================== 当前用户端点 ====================


@auth_router.get("/me", summary="Get current user")
async def get_me(user: User = Depends(get_current_user)) -> dict:
    """获取当前登录用户信息"""
    return _user_to_dict(user)


@auth_router.patch("/me", summary="Update profile")
async def update_me(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> dict:
    """更新个人信息"""
    updated = await service.update_profile(
        user.id,
        nickname=req.nickname,
        avatar=req.avatar,
        preferences=req.preferences,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(updated)


@auth_router.post("/sync", summary="Sync from Auth0")
async def sync_from_auth0(
    user: User = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> dict:
    """主动从 Auth0 同步用户信息到本地"""
    updated = await service.sync_from_auth0(user.id, credentials.credentials)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(updated)


# ==================== 管理员端点 ====================


@auth_router.get("/users", summary="List users (admin)")
async def list_users(
    role: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    admin: User = Depends(require_admin),
    service: UserService = Depends(_get_user_service),
) -> dict:
    users = await service.list_users(role=role, limit=limit, offset=offset)
    return {
        "users": [_user_to_dict(u) for u in users],
        "count": len(users),
    }


@auth_router.get("/users/{user_id}", summary="Get user (admin)")
async def get_user(
    user_id: str,
    admin: User = Depends(require_admin),
    service: UserService = Depends(_get_user_service),
) -> dict:
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


# ==================== 工具 ====================


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "auth0_id": user.auth0_id,
        "email": user.email,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "role": user.role,
        "permissions": user.permissions,
        "quota": user.quota,
        "subscription": user.subscription,
        "preferences": user.preferences,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
