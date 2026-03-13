"""
Auth 配置
优先级：os.environ > auth 包 .env > 默认值
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from load_env import load_module_env
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AuthConfig:
    """Auth0 配置"""

    # Auth0 租户域名，如 your-tenant.auth0.com
    domain: str = ""
    # API audience，如 https://your-api.example.com
    audience: str = ""
    # Auth0 应用 Client ID
    client_id: str = ""
    # Token 签名算法
    algorithms: List[str] = field(default_factory=lambda: ["RS256"])
    # MongoDB 集合名
    collection: str = "users"
    # JWKS 缓存时间（秒）
    jwks_cache_ttl: int = 3600

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}/"

    @property
    def jwks_url(self) -> str:
        return f"https://{self.domain}/.well-known/jwks.json"

    @property
    def userinfo_url(self) -> str:
        return f"https://{self.domain}/userinfo"

    @classmethod
    def from_env(cls) -> "AuthConfig":
        load_module_env(__file__)
        algos = os.getenv("AUTH0_ALGORITHMS", "RS256")
        config = cls(
            domain=os.getenv("AUTH0_DOMAIN", cls.domain),
            audience=os.getenv("AUTH0_AUDIENCE", cls.audience),
            client_id=os.getenv("AUTH0_CLIENT_ID", cls.client_id),
            algorithms=[a.strip() for a in algos.split(",")],
            collection=os.getenv("AUTH_USER_COLLECTION", cls.collection),
        )
        # 打印加载的配置，client_id 脱敏
        masked_cid = (
            f"{config.client_id[:6]}...{config.client_id[-4:]}"
            if len(config.client_id) > 10
            else config.client_id or "(空)"
        )
        logger.debug(
            "[Auth] 配置已加载 | domain=%s | audience=%s | client_id=%s | algorithms=%s | collection=%s",
            config.domain or "(空)",
            config.audience or "(空)",
            masked_cid,
            config.algorithms,
            config.collection,
        )
        return config


default_config = AuthConfig()
