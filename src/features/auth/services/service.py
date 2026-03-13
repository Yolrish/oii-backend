"""
用户服务

查找/创建/更新/同步用户信息。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..configs.config import AuthConfig
from ..models.models import User, UserRole
from ..providers.auth0 import Auth0Provider
from ..repositories import repository as repo
from utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    """
    用户管理服务

    核心流程：通过 auth0_id 查找用户，不存在则从 Auth0 拉取信息并创建。
    """

    def __init__(
        self,
        db: Any,
        config: Optional[AuthConfig] = None,
        auth0_provider: Optional[Auth0Provider] = None,
    ):
        self.db = db
        self.config = config or AuthConfig.from_env()
        self.auth0 = auth0_provider or Auth0Provider(self.config)

    async def get_or_create_by_token(
        self, auth0_id: str, access_token: str,
    ) -> User:
        """
        核心方法：通过 auth0_id 获取用户，不存在则从 Auth0 拉取并创建

        在认证依赖中调用：每次请求验证 token 后，用此方法获取本地用户。
        """
        logger.debug("[UserService] 查找用户 auth0_id=%s | collection=%s", auth0_id, self.config.collection)
        user = await repo.load_user_by_auth0_id(
            self.db, self.config.collection, auth0_id,
        )
        if user:
            logger.debug("[UserService] 已找到用户 id=%s，更新 last_login", user.id)
            user.last_login_at = datetime.utcnow()
            await repo.update_user(self.db, self.config.collection, user)
            return user

        logger.debug("[UserService] 未找到用户，从 Auth0 获取 userinfo 并创建新用户...")
        userinfo = await self.auth0.get_userinfo(access_token)
        user = User(
            auth0_id=auth0_id,
            email=userinfo.get("email", ""),
            nickname=userinfo.get("nickname", userinfo.get("name", "")),
            avatar=userinfo.get("picture", ""),
        )
        await repo.save_user(self.db, self.config.collection, user)
        logger.debug("[UserService] 新用户已创建 id=%s | email=%s", user.id, user.email)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return await repo.load_user(self.db, self.config.collection, user_id)

    async def get_by_auth0_id(self, auth0_id: str) -> Optional[User]:
        return await repo.load_user_by_auth0_id(
            self.db, self.config.collection, auth0_id,
        )

    async def update_profile(
        self,
        user_id: str,
        nickname: Optional[str] = None,
        avatar: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[User]:
        """更新用户个人信息"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        if nickname is not None:
            user.nickname = nickname
        if avatar is not None:
            user.avatar = avatar
        if preferences is not None:
            user.preferences = preferences
        await repo.update_user(self.db, self.config.collection, user)
        return user

    async def sync_from_auth0(self, user_id: str, access_token: str) -> Optional[User]:
        """主动从 Auth0 同步用户信息"""
        logger.debug("[UserService] 同步 Auth0 信息 user_id=%s", user_id)
        user = await self.get_by_id(user_id)
        if not user:
            logger.warning("[UserService] 同步失败，用户不存在 user_id=%s", user_id)
            return None
        userinfo = await self.auth0.get_userinfo(access_token)
        user.email = userinfo.get("email", user.email)
        user.nickname = userinfo.get("nickname", userinfo.get("name", user.nickname))
        user.avatar = userinfo.get("picture", user.avatar)
        await repo.update_user(self.db, self.config.collection, user)
        logger.debug("[UserService] 同步完成 user_id=%s | email=%s", user.id, user.email)
        return user

    async def list_users(
        self,
        role: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[User]:
        return await repo.list_users(
            self.db, self.config.collection,
            role=role, limit=limit, offset=offset,
        )


def create_user_service(
    db: Any,
    config: Optional[AuthConfig] = None,
) -> UserService:
    return UserService(db, config)
