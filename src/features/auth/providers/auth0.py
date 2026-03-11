"""
Auth0 Token 验证 + userinfo 获取

使用 PyJWT + JWKS 公钥验证 Access Token，支持公钥缓存。
"""

import time
from typing import Any, Dict, Optional

import httpx
import jwt

from ..configs.config import AuthConfig


class Auth0Provider:
    """
    Auth0 认证提供者

    职责：
    1. 从 JWKS 端点获取并缓存公钥
    2. 验证 Access Token（签名、过期、audience、issuer）
    3. 从 /userinfo 端点获取用户完整信息
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig.from_env()
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_fetched_at: float = 0

    def _should_refresh_jwks(self) -> bool:
        if not self._jwks:
            return True
        return (time.time() - self._jwks_fetched_at) > self.config.jwks_cache_ttl

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """获取 JWKS 公钥集"""
        if not self._should_refresh_jwks():
            return self._jwks
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.config.jwks_url, timeout=10)
            resp.raise_for_status()
            self._jwks = resp.json()
            self._jwks_fetched_at = time.time()
            return self._jwks

    def _get_signing_key(self, jwks: Dict[str, Any], token: str) -> str:
        """从 JWKS 中找到与 token header kid 匹配的公钥"""
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise jwt.InvalidTokenError("Token header missing kid")
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(key)
        raise jwt.InvalidTokenError(f"No matching key found for kid: {kid}")

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证 Access Token

        Returns:
            解码后的 payload（含 sub、email、permissions 等）

        Raises:
            jwt.InvalidTokenError: Token 无效
        """
        jwks = await self._fetch_jwks()
        signing_key = self._get_signing_key(jwks, token)
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=self.config.algorithms,
            audience=self.config.audience,
            issuer=self.config.issuer,
        )
        return payload

    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """
        调用 Auth0 /userinfo 端点获取用户完整信息

        Returns:
            {"sub": "auth0|xxx", "email": "...", "nickname": "...", "picture": "...", ...}
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.config.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
