# Twitter/X API 模块

封装 X (Twitter) 官方 API v2，提供推文、用户、时间线、互动等操作。

## 模块结构

```
twitter/
├── client.py        # TwitterConfig + TwitterClient（配置、OAuth 签名、HTTP、业务方法）
├── models.py        # 数据模型（Tweet, User, TweetList 等）
├── exceptions.py    # 异常层级
└── .env.example     # 环境变量模板
```

## 配置

在项目根 `.env` 或本包 `.env` 中配置，凭据在 [X Developer Portal](https://developer.x.com/portal) 获取：

```env
# OAuth 1.0a — 写操作（发推、点赞、转推、关注等）
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=

# Bearer Token — 只读操作（搜索、查询用户等）
TWITTER_BEARER_TOKEN=
```

可选配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TWITTER_BASE_URL` | `https://api.twitter.com/2` | API 基础地址 |
| `TWITTER_TIMEOUT` | `30` | 请求超时（秒） |

## 认证方式

| 方式 | 适用场景 | 所需凭据 |
|------|---------|---------|
| OAuth 1.0a | 发推、删推、点赞、转推、关注等写操作 | API Key/Secret + Access Token/Secret |
| Bearer Token | 搜索推文、查询用户、获取时间线等只读操作 | Bearer Token |

客户端内置 OAuth 1.0a HMAC-SHA1 签名（RFC 5849），无需额外依赖。

## 使用示例

```python
from packages.twitter import TwitterClient, create_twitter_client

# 方式一：上下文管理器
async with TwitterClient() as client:
    tweet = await client.post_tweet("Hello from API!")
    user  = await client.get_user_by_username("elonmusk")

# 方式二：工厂函数
client = create_twitter_client()
results = await client.search_recent("python", max_results=20)
await client.close()
```

自定义配置：

```python
from packages.twitter import TwitterConfig, TwitterClient

config = TwitterConfig(
    bearer_token="your-token",
    timeout=60,
)
client = TwitterClient(config)
```

## API 一览

### 推文

| 方法 | 说明 | 认证 |
|------|------|------|
| `post_tweet(text, *, reply_to_tweet_id, quote_tweet_id)` | 发送推文 / 回复 / 引用转推 | OAuth 1.0a |
| `delete_tweet(tweet_id)` | 删除推文 | OAuth 1.0a |
| `get_tweet(tweet_id)` | 获取推文详情 | Bearer |
| `search_recent(query, *, max_results, next_token)` | 搜索近 7 天推文 | Bearer |

### 用户

| 方法 | 说明 | 认证 |
|------|------|------|
| `get_me()` | 获取当前认证用户 | OAuth 1.0a |
| `get_user(user_id)` | 通过 ID 获取用户 | Bearer |
| `get_user_by_username(username)` | 通过用户名获取用户 | Bearer |

### 时间线

| 方法 | 说明 | 认证 |
|------|------|------|
| `get_user_tweets(user_id, *, max_results, next_token)` | 用户推文时间线 | Bearer |
| `get_user_mentions(user_id, *, max_results, next_token)` | 提及用户的推文 | Bearer |

### 互动

| 方法 | 说明 | 认证 |
|------|------|------|
| `like(tweet_id)` / `unlike(tweet_id)` | 点赞 / 取消点赞 | OAuth 1.0a |
| `retweet(tweet_id)` / `undo_retweet(tweet_id)` | 转推 / 取消转推 | OAuth 1.0a |

### 关注

| 方法 | 说明 | 认证 |
|------|------|------|
| `follow(target_user_id)` / `unfollow(target_user_id)` | 关注 / 取消关注 | OAuth 1.0a |
| `get_followers(user_id, *, max_results, next_token)` | 获取粉丝列表 | Bearer |
| `get_following(user_id, *, max_results, next_token)` | 获取关注列表 | Bearer |

## 异常处理

所有异常继承自 `TwitterError`，包含 `status_code` 和 `response_data` 属性：

```python
from packages.twitter import TwitterClient, TwitterRateLimitError, TwitterAuthError

async with TwitterClient() as client:
    try:
        await client.search_recent("python")
    except TwitterRateLimitError as e:
        print(f"速率限制，重置时间: {e.reset_at}")
    except TwitterAuthError:
        print("认证失败，检查凭据配置")
```

| 异常 | HTTP 状态码 | 说明 |
|------|------------|------|
| `TwitterAuthError` | 401 / 403 | 认证失败 |
| `TwitterRateLimitError` | 429 | 速率限制（含 `reset_at` 时间戳） |
| `TwitterNotFoundError` | 404 | 资源不存在 |
| `TwitterBadRequestError` | 400 | 请求参数错误 |
| `TwitterConfigError` | — | 配置缺失 |

## 数据模型

| 模型 | 说明 |
|------|------|
| `Tweet` | 推文（含 `public_metrics`、`from_api()` 工厂方法） |
| `User` | 用户（含 `public_metrics`、`from_api()` 工厂方法） |
| `TweetList` | 推文列表 + 分页信息（`tweets` + `meta`） |
| `PaginationMeta` | 分页元数据（`next_token`、`result_count`） |

所有模型均提供 `from_api()` 类方法从 API v2 原始 JSON 构建，并保留 `raw` 字段存储未解析数据。
