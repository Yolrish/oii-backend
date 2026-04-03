"""
Twitter/X API 模块

封装 X (Twitter) 官方 API v2，提供推文发送、搜索、用户查询、互动等功能。
支持 OAuth 1.0a（用户上下文写操作）和 Bearer Token（应用级只读操作）两种认证。
"""

from .client import (
    TwitterConfig,
    TwitterClient,
    get_default_client,
    create_twitter_client,
)
from .models import (
    ReplySettings,
    TweetPublicMetrics,
    UserPublicMetrics,
    Tweet,
    User,
    PaginationMeta,
    TweetList,
)
from .exceptions import (
    TwitterError,
    TwitterAuthError,
    TwitterRateLimitError,
    TwitterNotFoundError,
    TwitterBadRequestError,
    TwitterConfigError,
)

__all__ = [
    # 客户端
    "TwitterConfig",
    "TwitterClient",
    "get_default_client",
    "create_twitter_client",
    # 模型
    "ReplySettings",
    "TweetPublicMetrics",
    "UserPublicMetrics",
    "Tweet",
    "User",
    "PaginationMeta",
    "TweetList",
    # 异常
    "TwitterError",
    "TwitterAuthError",
    "TwitterRateLimitError",
    "TwitterNotFoundError",
    "TwitterBadRequestError",
    "TwitterConfigError",
]

__version__ = "1.0.0"
