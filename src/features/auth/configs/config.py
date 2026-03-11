"""
Auth 配置
优先级：os.environ > auth 包 .env > 默认值
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from load_env import load_module_env


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
        return cls(
            domain=os.getenv("AUTH0_DOMAIN", cls.domain),
            audience=os.getenv("AUTH0_AUDIENCE", cls.audience),
            client_id=os.getenv("AUTH0_CLIENT_ID", cls.client_id),
            algorithms=[a.strip() for a in algos.split(",")],
            collection=os.getenv("AUTH_USER_COLLECTION", cls.collection),
        )


default_config = AuthConfig()
