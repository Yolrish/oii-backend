"""
Auth0 Token 验证 + userinfo 获取

使用 PyJWT + JWKS 公钥验证 Access Token，支持公钥缓存。
"""

import time
from typing import Any, Dict, Optional

import httpx
import jwt

from ..configs.config import AuthConfig
from utils.logger import get_logger

logger = get_logger(__name__)


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
            logger.debug("[Auth0] 使用缓存的 JWKS 公钥")
            return self._jwks
        logger.debug("[Auth0] 正在从 %s 获取 JWKS 公钥...", self.config.jwks_url)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.config.jwks_url, timeout=10)
                resp.raise_for_status()
                self._jwks = resp.json()
                self._jwks_fetched_at = time.time()
                key_count = len(self._jwks.get("keys", []))
                logger.debug("[Auth0] JWKS 获取成功，包含 %d 个公钥", key_count)
                return self._jwks
        except httpx.HTTPError as e:
            logger.error("[Auth0] JWKS 获取失败: %s", e)
            raise

    def _get_signing_key(self, jwks: Dict[str, Any], token: str) -> str:
        """从 JWKS 中找到与 token header kid 匹配的公钥"""
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        logger.debug("[Auth0] Token header: alg=%s, kid=%s", unverified_header.get("alg"), kid)
        if not kid:
            logger.warning("[Auth0] Token header 缺少 kid")
            raise jwt.InvalidTokenError("Token header missing kid")
        available_kids = [k.get("kid") for k in jwks.get("keys", [])]
        logger.debug("[Auth0] JWKS 可用 kid 列表: %s", available_kids)
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                logger.debug("[Auth0] 匹配到公钥 kid=%s", kid)
                return jwt.algorithms.RSAAlgorithm.from_jwk(key)
        logger.warning("[Auth0] 未找到匹配的公钥 kid=%s", kid)
        raise jwt.InvalidTokenError(f"No matching key found for kid: {kid}")

    def _is_opaque_token(self, token: str) -> bool:
        """判断是否为不透明 Token（Auth0 在未指定 audience 时返回 JWE，alg=dir）"""
        try:
            header = jwt.get_unverified_header(token)
            return header.get("alg") == "dir" or not header.get("kid")
        except jwt.exceptions.DecodeError:
            return True

    async def _verify_via_userinfo(self, token: str) -> Dict[str, Any]:
        """
        通过 /userinfo 端点验证不透明 Token

        Auth0 会校验 Token 有效性，有效则返回用户信息，无效则 401。
        将 userinfo 响应转换为与 JWT payload 兼容的格式。
        """
        logger.debug("[Auth0] 不透明 Token，改用 /userinfo 端点验证")
        info = await self.get_userinfo(token)
        sub = info.get("sub", "")
        if not sub:
            raise jwt.InvalidTokenError("userinfo 响应缺少 sub 字段")
        # 构造与 JWT payload 兼容的结果
        payload = {
            "sub": sub,
            "email": info.get("email"),
            "nickname": info.get("nickname"),
            "name": info.get("name"),
            "picture": info.get("picture"),
            "email_verified": info.get("email_verified"),
        }
        logger.debug("[Auth0] /userinfo 验证通过 | sub=%s | email=%s", sub, info.get("email"))
        return payload

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证 Access Token

        优先用 JWKS 本地验证（RS256 JWT），
        如果是不透明 Token（alg=dir）则 fallback 到 /userinfo 端点验证。

        Returns:
            解码后的 payload（含 sub、email 等）

        Raises:
            jwt.InvalidTokenError: Token 无效
            httpx.HTTPStatusError: /userinfo 请求失败（Token 无效）
        """
        logger.debug("[Auth0] 开始验证 Token (前16字符: %s...)", token[:16] if len(token) > 16 else token)

        # 不透明 Token → 走 /userinfo 远程验证
        if self._is_opaque_token(token):
            logger.debug("[Auth0] 检测到不透明 Token (alg=dir)，将通过 /userinfo 验证")
            return await self._verify_via_userinfo(token)

        # 标准 JWT → 走 JWKS 本地验证
        logger.debug("[Auth0] 标准 JWT，走 JWKS 本地验证 | audience=%s | issuer=%s | algorithms=%s",
                     self.config.audience, self.config.issuer, self.config.algorithms)
        jwks = await self._fetch_jwks()
        signing_key = self._get_signing_key(jwks, token)
        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=self.config.algorithms,
                audience=self.config.audience,
                issuer=self.config.issuer,
            )
            logger.debug("[Auth0] Token 验证通过 | sub=%s | exp=%s", payload.get("sub"), payload.get("exp"))
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("[Auth0] Token 已过期")
            raise
        except jwt.InvalidAudienceError:
            logger.warning("[Auth0] Token audience 不匹配，期望: %s", self.config.audience)
            raise
        except jwt.InvalidIssuerError:
            logger.warning("[Auth0] Token issuer 不匹配，期望: %s", self.config.issuer)
            raise
        except jwt.InvalidTokenError as e:
            logger.warning("[Auth0] Token 验证失败: %s", e)
            raise

    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """
        调用 Auth0 /userinfo 端点获取用户完整信息

        Returns:
            {"sub": "auth0|xxx", "email": "...", "nickname": "...", "picture": "...", ...}
        """
        logger.debug("[Auth0] 正在从 %s 获取 userinfo...", self.config.userinfo_url)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.config.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                resp.raise_for_status()
                info = resp.json()
                logger.debug("[Auth0] userinfo 获取成功 | sub=%s | email=%s", info.get("sub"), info.get("email"))
                return info
        except httpx.HTTPError as e:
            logger.error("[Auth0] userinfo 获取失败: %s", e)
            raise
