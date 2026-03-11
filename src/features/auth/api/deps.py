"""
认证依赖注入

提供 get_current_user / get_optional_user / require_admin，
供所有需要认证的路由使用。
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.mongodb import get_database
from ..configs.config import AuthConfig
from ..models.models import User, UserRole
from ..providers.auth0 import Auth0Provider
from ..services.service import UserService

# Bearer token 提取
_bearer_scheme = HTTPBearer(auto_error=False)

# 模块级单例（避免每次请求重建）
_config: Optional[AuthConfig] = None
_auth0: Optional[Auth0Provider] = None


def _get_config() -> AuthConfig:
    global _config
    if _config is None:
        _config = AuthConfig.from_env()
    return _config


def _get_auth0() -> Auth0Provider:
    global _auth0
    if _auth0 is None:
        _auth0 = Auth0Provider(_get_config())
    return _auth0


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> User:
    """
    认证依赖：验证 Bearer Token，返回本地 User 对象

    流程：
    1. 提取 Bearer token
    2. 通过 Auth0 JWKS 验证签名
    3. 从 DB 获取用户（不存在则从 Auth0 拉取并创建）
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    config = _get_config()
    auth0 = _get_auth0()

    try:
        payload = await auth0.verify_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth0_id = payload.get("sub", "")
    if not auth0_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )

    db = get_database()
    svc = UserService(db, config, auth0)
    user = await svc.get_or_create_by_token(auth0_id, token)
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[User]:
    """可选认证：有 token 则返回 User，无则返回 None"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """要求管理员权限"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
