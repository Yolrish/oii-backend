"""
Twitter/X API 数据模型

基于 X API v2 响应格式，使用 dataclass 保持与项目风格一致。
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class ReplySettings(str, Enum):
    """推文回复权限"""
    EVERYONE = "everyone"
    MENTIONED_USERS = "mentionedUsers"
    FOLLOWERS = "following"


@dataclass
class TweetPublicMetrics:
    """推文公开指标"""
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    impression_count: int = 0


@dataclass
class UserPublicMetrics:
    """用户公开指标"""
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    listed_count: int = 0


@dataclass
class Tweet:
    """推文数据模型"""
    id: str = ""
    text: str = ""
    author_id: str = ""
    conversation_id: str = ""
    created_at: str = ""
    lang: str = ""
    edit_history_tweet_ids: List[str] = field(default_factory=list)
    public_metrics: Optional[TweetPublicMetrics] = None
    reply_settings: str = ""
    in_reply_to_user_id: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Tweet":
        """从 API v2 响应数据构建"""
        metrics = data.get("public_metrics")
        public_metrics = None
        if metrics:
            public_metrics = TweetPublicMetrics(
                retweet_count=metrics.get("retweet_count", 0),
                reply_count=metrics.get("reply_count", 0),
                like_count=metrics.get("like_count", 0),
                quote_count=metrics.get("quote_count", 0),
                bookmark_count=metrics.get("bookmark_count", 0),
                impression_count=metrics.get("impression_count", 0),
            )
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            author_id=data.get("author_id", ""),
            conversation_id=data.get("conversation_id", ""),
            created_at=data.get("created_at", ""),
            lang=data.get("lang", ""),
            edit_history_tweet_ids=data.get("edit_history_tweet_ids", []),
            public_metrics=public_metrics,
            reply_settings=data.get("reply_settings", ""),
            in_reply_to_user_id=data.get("in_reply_to_user_id", ""),
            raw=data,
        )


@dataclass
class User:
    """用户数据模型"""
    id: str = ""
    name: str = ""
    username: str = ""
    description: str = ""
    created_at: str = ""
    profile_image_url: str = ""
    location: str = ""
    url: str = ""
    verified: bool = False
    protected: bool = False
    public_metrics: Optional[UserPublicMetrics] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "User":
        """从 API v2 响应数据构建"""
        metrics = data.get("public_metrics")
        public_metrics = None
        if metrics:
            public_metrics = UserPublicMetrics(
                followers_count=metrics.get("followers_count", 0),
                following_count=metrics.get("following_count", 0),
                tweet_count=metrics.get("tweet_count", 0),
                listed_count=metrics.get("listed_count", 0),
            )
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            username=data.get("username", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            profile_image_url=data.get("profile_image_url", ""),
            location=data.get("location", ""),
            url=data.get("url", ""),
            verified=data.get("verified", False),
            protected=data.get("protected", False),
            public_metrics=public_metrics,
            raw=data,
        )


@dataclass
class PaginationMeta:
    """分页元数据"""
    result_count: int = 0
    next_token: str = ""
    previous_token: str = ""

    @classmethod
    def from_api(cls, meta: Dict[str, Any]) -> "PaginationMeta":
        return cls(
            result_count=meta.get("result_count", 0),
            next_token=meta.get("next_token", ""),
            previous_token=meta.get("previous_token", ""),
        )


@dataclass
class TweetList:
    """推文列表（搜索结果 / 时间线）"""
    tweets: List[Tweet] = field(default_factory=list)
    meta: Optional[PaginationMeta] = None

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "TweetList":
        """从 API v2 响应数据构建"""
        tweets_data = data.get("data", [])
        tweets = [Tweet.from_api(t) for t in tweets_data] if tweets_data else []
        meta = None
        if "meta" in data:
            meta = PaginationMeta.from_api(data["meta"])
        return cls(tweets=tweets, meta=meta)
