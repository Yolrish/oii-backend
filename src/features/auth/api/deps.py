"""
认证依赖注入

提供 get_current_user / get_optional_user / require_admin，
供所有需要认证的路由使用。
"""

from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.mongodb import get_database
from ..configs.config import AuthConfig
from ..models.models import User, UserRole
from ..providers.auth0 import Auth0Provider
from ..services.service import UserService
from utils.logger import get_logger

logger = get_logger(__name__)

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
        logger.debug("[AuthDeps] 请求未携带 Bearer Token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    logger.debug("[AuthDeps] 收到 Bearer Token (前16字符: %s...)", token[:16] if len(token) > 16 else token)
    config = _get_config()
    auth0 = _get_auth0()

    try:
        payload = await auth0.verify_token(token)
    except httpx.HTTPStatusError as e:
        # /userinfo 返回 401/403 等，说明 Token 无效或已过期
        logger.warning("[AuthDeps] Token 远程验证失败 (HTTP %s): %s", e.response.status_code, e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.warning("[AuthDeps] Token 验证失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth0_id = payload.get("sub", "")
    if not auth0_id:
        logger.warning("[AuthDeps] Token payload 缺少 sub 字段")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )

    logger.debug("[AuthDeps] Token 验证通过，查找/创建用户 auth0_id=%s", auth0_id)
    db = get_database()
    svc = UserService(db, config, auth0)
    user = await svc.get_or_create_by_token(auth0_id, token)
    logger.debug("[AuthDeps] 认证完成 user_id=%s | role=%s", user.id, user.role)
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[User]:
    """可选认证：有 token 则返回 User，无则返回 None"""
    if not credentials:
        logger.debug("[AuthDeps] 可选认证：未携带 Token，返回 None")
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        logger.debug("[AuthDeps] 可选认证：Token 无效，返回 None")
        return None


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """要求管理员权限"""
    if user.role != UserRole.ADMIN:
        logger.warning("[AuthDeps] 权限不足 user_id=%s role=%s，需要 admin", user.id, user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
