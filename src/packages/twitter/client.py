"""
Twitter/X API 客户端

将配置、OAuth 1.0a 签名、HTTP 请求、业务方法统一封装在 TwitterClient 中。
OAuth 1.0a 签名基于 RFC 5849 实现，不依赖第三方 OAuth 库。
"""
import os
import hashlib
import hmac
import base64
import time
import secrets
from urllib.parse import quote, urlparse
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal

import httpx

from load_env import load_module_env

from .exceptions import (
    TwitterError,
    TwitterAuthError,
    TwitterRateLimitError,
    TwitterNotFoundError,
    TwitterBadRequestError,
    TwitterConfigError,
)
from .models import Tweet, User, TweetList

# 加载 twitter 包 .env（不覆盖已有变量）
load_module_env(__file__)

AuthMethod = Literal["oauth1", "bearer"]

# X API v2 常用的字段展开参数
_TWEET_FIELDS = "author_id,created_at,conversation_id,lang,public_metrics,reply_settings"
_USER_FIELDS = "created_at,description,location,profile_image_url,public_metrics,url,verified,protected"


@dataclass
class TwitterConfig:
    """Twitter API 凭据与选项"""

    # OAuth 1.0a（用户上下文写操作：发推、点赞等）
    api_key: str = field(
        default_factory=lambda: os.environ.get("TWITTER_API_KEY", "")
    )
    api_secret: str = field(
        default_factory=lambda: os.environ.get("TWITTER_API_SECRET", "")
    )
    access_token: str = field(
        default_factory=lambda: os.environ.get("TWITTER_ACCESS_TOKEN", "")
    )
    access_token_secret: str = field(
        default_factory=lambda: os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
    )

    # Bearer Token（应用级只读操作：搜索、查询用户等）
    bearer_token: str = field(
        default_factory=lambda: os.environ.get("TWITTER_BEARER_TOKEN", "")
    )

    # API 基础地址 / 超时
    base_url: str = field(
        default_factory=lambda: os.environ.get("TWITTER_BASE_URL", "https://api.twitter.com/2")
    )
    timeout: int = field(
        default_factory=lambda: int(os.environ.get("TWITTER_TIMEOUT", "30"))
    )

    @property
    def has_oauth1(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token and self.access_token_secret)

    @property
    def has_bearer(self) -> bool:
        return bool(self.bearer_token)


class TwitterClient:
    """
    Twitter/X API v2 客户端

    集成配置读取、OAuth 1.0a 签名、HTTP 请求和所有业务方法。

    使用示例::

        async with TwitterClient() as client:
            tweet = await client.post_tweet("Hello!")
            user  = await client.get_user_by_username("elonmusk")
            await client.like(tweet.id)
    """

    def __init__(self, config: Optional[TwitterConfig] = None):
        self.config = config or TwitterConfig()
        self._http: Optional[httpx.AsyncClient] = None
        # 缓存当前认证用户 ID，点赞/转推等操作需要
        self._my_user_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    #  HTTP 基础设施
    # ------------------------------------------------------------------ #

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=self.config.timeout)
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    # ------------------------------------------------------------------ #
    #  OAuth 1.0a 签名（RFC 5849）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _pct(s: str) -> str:
        """百分比编码"""
        return quote(str(s), safe="")

    def _sign(
        self,
        method: str,
        url: str,
        query_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """生成 OAuth Authorization 头"""
        oauth = {
            "oauth_consumer_key": self.config.api_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.config.access_token,
            "oauth_version": "1.0",
        }

        # 合并参与签名的参数（JSON body 不参与）
        all_params = {**oauth, **(query_params or {})}
        param_str = "&".join(
            f"{self._pct(k)}={self._pct(v)}" for k, v in sorted(all_params.items())
        )

        # 签名基础字符串
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        base_string = f"{method.upper()}&{self._pct(base_url)}&{self._pct(param_str)}"

        # HMAC-SHA1
        key = f"{self._pct(self.config.api_secret)}&{self._pct(self.config.access_token_secret)}"
        sig = base64.b64encode(
            hmac.new(key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        oauth["oauth_signature"] = sig

        parts = ", ".join(f'{self._pct(k)}="{self._pct(v)}"' for k, v in sorted(oauth.items()))
        return f"OAuth {parts}"

    # ------------------------------------------------------------------ #
    #  通用请求
    # ------------------------------------------------------------------ #

    def _url(self, endpoint: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _auth_header(
        self,
        method: str,
        url: str,
        auth: AuthMethod,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        if auth == "oauth1":
            if not self.config.has_oauth1:
                raise TwitterConfigError(
                    "需要 OAuth 1.0a 凭据 (API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)"
                )
            return {"Authorization": self._sign(method, url, query_params)}
        if not self.config.has_bearer:
            raise TwitterConfigError("需要 Bearer Token")
        return {"Authorization": f"Bearer {self.config.bearer_token}"}

    def _raise_for_status(self, resp: httpx.Response) -> None:
        """将 HTTP 错误码映射为具体异常"""
        if resp.status_code < 400:
            return
        try:
            data = resp.json()
        except Exception:
            data = {"detail": resp.text}
        code = resp.status_code
        if code in (401, 403):
            raise TwitterAuthError(f"认证失败 ({code})", status_code=code, response_data=data)
        if code == 429:
            raise TwitterRateLimitError(
                reset_at=int(resp.headers.get("x-rate-limit-reset", "0")),
                status_code=code,
                response_data=data,
            )
        if code == 404:
            raise TwitterNotFoundError(str(data), status_code=code, response_data=data)
        if code == 400:
            raise TwitterBadRequestError(f"请求错误: {data}", status_code=code, response_data=data)
        raise TwitterError(f"API 错误 ({code})", status_code=code, response_data=data)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        auth: AuthMethod = "bearer",
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = self._url(endpoint)
        str_params = {k: str(v) for k, v in params.items() if v is not None} if params else None
        headers = self._auth_header(method, url, auth, str_params)
        if json is not None:
            headers["Content-Type"] = "application/json"

        resp = await self._client.request(method, url, headers=headers, params=params, json=json)
        self._raise_for_status(resp)
        return resp.json() if resp.status_code != 204 else {}

    # ------------------------------------------------------------------ #
    #  推文
    # ------------------------------------------------------------------ #

    async def post_tweet(
        self,
        text: str,
        *,
        reply_to_tweet_id: Optional[str] = None,
        quote_tweet_id: Optional[str] = None,
    ) -> Tweet:
        """
        发送推文

        Args:
            text: 推文内容
            reply_to_tweet_id: 回复目标推文 ID
            quote_tweet_id: 引用转推目标 ID
        """
        body: Dict[str, Any] = {"text": text}
        if reply_to_tweet_id:
            body["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}
        if quote_tweet_id:
            body["quote_tweet_id"] = quote_tweet_id

        resp = await self._request("POST", "/tweets", auth="oauth1", json=body)
        return Tweet.from_api(resp.get("data", {}))

    async def delete_tweet(self, tweet_id: str) -> bool:
        """删除推文"""
        resp = await self._request("DELETE", f"/tweets/{tweet_id}", auth="oauth1")
        return resp.get("data", {}).get("deleted", False)

    async def get_tweet(self, tweet_id: str, *, tweet_fields: Optional[str] = None) -> Tweet:
        """获取单条推文详情"""
        params = {"tweet.fields": tweet_fields or _TWEET_FIELDS}
        resp = await self._request("GET", f"/tweets/{tweet_id}", params=params)
        return Tweet.from_api(resp.get("data", {}))

    async def search_recent(
        self,
        query: str,
        *,
        max_results: int = 10,
        next_token: Optional[str] = None,
        tweet_fields: Optional[str] = None,
    ) -> TweetList:
        """
        搜索近期推文（7 天内）

        Args:
            query: 搜索查询（支持 X 搜索运算符）
            max_results: 每页结果数（10-100）
            next_token: 分页令牌
        """
        params: Dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": tweet_fields or _TWEET_FIELDS,
        }
        if next_token:
            params["next_token"] = next_token
        resp = await self._request("GET", "/tweets/search/recent", params=params)
        return TweetList.from_api(resp)

    # ------------------------------------------------------------------ #
    #  用户
    # ------------------------------------------------------------------ #

    async def get_me(self, *, user_fields: Optional[str] = None) -> User:
        """获取当前认证用户信息"""
        params = {"user.fields": user_fields or _USER_FIELDS}
        resp = await self._request("GET", "/users/me", auth="oauth1", params=params)
        user = User.from_api(resp.get("data", {}))
        self._my_user_id = user.id
        return user

    async def get_user(self, user_id: str, *, user_fields: Optional[str] = None) -> User:
        """通过 ID 获取用户"""
        params = {"user.fields": user_fields or _USER_FIELDS}
        resp = await self._request("GET", f"/users/{user_id}", params=params)
        return User.from_api(resp.get("data", {}))

    async def get_user_by_username(self, username: str, *, user_fields: Optional[str] = None) -> User:
        """通过用户名获取用户（不含 @）"""
        params = {"user.fields": user_fields or _USER_FIELDS}
        resp = await self._request("GET", f"/users/by/username/{username}", params=params)
        return User.from_api(resp.get("data", {}))

    # ------------------------------------------------------------------ #
    #  时间线
    # ------------------------------------------------------------------ #

    async def get_user_tweets(
        self,
        user_id: str,
        *,
        max_results: int = 10,
        next_token: Optional[str] = None,
        tweet_fields: Optional[str] = None,
    ) -> TweetList:
        """获取用户的推文时间线"""
        params: Dict[str, Any] = {
            "max_results": max_results,
            "tweet.fields": tweet_fields or _TWEET_FIELDS,
        }
        if next_token:
            params["next_token"] = next_token
        resp = await self._request("GET", f"/users/{user_id}/tweets", params=params)
        return TweetList.from_api(resp)

    async def get_user_mentions(
        self,
        user_id: str,
        *,
        max_results: int = 10,
        next_token: Optional[str] = None,
        tweet_fields: Optional[str] = None,
    ) -> TweetList:
        """获取提及用户的推文"""
        params: Dict[str, Any] = {
            "max_results": max_results,
            "tweet.fields": tweet_fields or _TWEET_FIELDS,
        }
        if next_token:
            params["next_token"] = next_token
        resp = await self._request("GET", f"/users/{user_id}/mentions", params=params)
        return TweetList.from_api(resp)

    # ------------------------------------------------------------------ #
    #  互动（点赞 / 转推）
    # ------------------------------------------------------------------ #

    async def _ensure_my_id(self) -> str:
        if not self._my_user_id:
            await self.get_me()
        return self._my_user_id  # type: ignore[return-value]

    async def like(self, tweet_id: str) -> bool:
        """点赞推文"""
        uid = await self._ensure_my_id()
        resp = await self._request("POST", f"/users/{uid}/likes", auth="oauth1", json={"tweet_id": tweet_id})
        return resp.get("data", {}).get("liked", False)

    async def unlike(self, tweet_id: str) -> bool:
        """取消点赞"""
        uid = await self._ensure_my_id()
        resp = await self._request("DELETE", f"/users/{uid}/likes/{tweet_id}", auth="oauth1")
        return not resp.get("data", {}).get("liked", True)

    async def retweet(self, tweet_id: str) -> bool:
        """转推"""
        uid = await self._ensure_my_id()
        resp = await self._request("POST", f"/users/{uid}/retweets", auth="oauth1", json={"tweet_id": tweet_id})
        return resp.get("data", {}).get("retweeted", False)

    async def undo_retweet(self, tweet_id: str) -> bool:
        """取消转推"""
        uid = await self._ensure_my_id()
        resp = await self._request("DELETE", f"/users/{uid}/retweets/{tweet_id}", auth="oauth1")
        return not resp.get("data", {}).get("retweeted", True)

    # ------------------------------------------------------------------ #
    #  关注
    # ------------------------------------------------------------------ #

    async def follow(self, target_user_id: str) -> bool:
        """关注用户"""
        uid = await self._ensure_my_id()
        resp = await self._request(
            "POST", f"/users/{uid}/following", auth="oauth1", json={"target_user_id": target_user_id}
        )
        return resp.get("data", {}).get("following", False)

    async def unfollow(self, target_user_id: str) -> bool:
        """取消关注"""
        uid = await self._ensure_my_id()
        resp = await self._request("DELETE", f"/users/{uid}/following/{target_user_id}", auth="oauth1")
        return not resp.get("data", {}).get("following", True)

    async def get_followers(
        self,
        user_id: str,
        *,
        max_results: int = 100,
        next_token: Optional[str] = None,
        user_fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取粉丝列表，返回 {"users": [...], "meta": {...}}"""
        params: Dict[str, Any] = {
            "max_results": max_results,
            "user.fields": user_fields or _USER_FIELDS,
        }
        if next_token:
            params["pagination_token"] = next_token
        resp = await self._request("GET", f"/users/{user_id}/followers", params=params)
        return {
            "users": [User.from_api(u) for u in resp.get("data", [])],
            "meta": resp.get("meta", {}),
        }

    async def get_following(
        self,
        user_id: str,
        *,
        max_results: int = 100,
        next_token: Optional[str] = None,
        user_fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取关注列表，返回 {"users": [...], "meta": {...}}"""
        params: Dict[str, Any] = {
            "max_results": max_results,
            "user.fields": user_fields or _USER_FIELDS,
        }
        if next_token:
            params["pagination_token"] = next_token
        resp = await self._request("GET", f"/users/{user_id}/following", params=params)
        return {
            "users": [User.from_api(u) for u in resp.get("data", [])],
            "meta": resp.get("meta", {}),
        }


# ==================== 工厂函数 ====================

_default_client: Optional[TwitterClient] = None


def get_default_client() -> TwitterClient:
    """获取默认客户端实例（懒加载单例）"""
    global _default_client
    if _default_client is None:
        _default_client = TwitterClient()
    return _default_client


def create_twitter_client(config: Optional[TwitterConfig] = None) -> TwitterClient:
    """创建新的客户端实例"""
    return TwitterClient(config=config)
