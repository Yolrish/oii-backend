# Auth 用户系统

基于 Auth0 的用户认证与管理。前端通过 auth0-spa-js 登录，后端验证 Token 并同步用户信息到 MongoDB。

## 模块结构

```
features/auth/
├── configs/config.py              # Auth0 域名、audience、JWKS URL
├── models/models.py               # User 数据模型
├── providers/auth0.py             # Token 验证（JWKS 公钥）+ /userinfo 获取
├── repositories/repository.py     # MongoDB 用户 CRUD
├── services/service.py            # UserService
├── api/
│   ├── deps.py                    # 认证依赖注入
│   └── routes.py                  # HTTP 端点
└── README.md
```

## 认证流程

```
前端 auth0-spa-js 登录 → 获取 Access Token
    → 请求后端（Bearer Token）
    → deps.py: get_current_user
        → Auth0Provider.verify_token（JWKS 公钥验证签名、过期、audience）
        → UserService.get_or_create_by_token
            → 查 MongoDB（auth0_id）
            → 有 → 更新 last_login → 返回 User
            → 无 → 调 Auth0 /userinfo → 创建用户 → 返回 User
    → 路由拿到 User 对象
```

## 认证依赖

其他模块通过 FastAPI Depends 注入用户：

```python
from features.auth import get_current_user, get_optional_user, require_admin
from features.auth.models import User

# 必须登录
@router.get("/xxx")
async def handler(user: User = Depends(get_current_user)):
    ...

# 可选登录
@router.get("/yyy")
async def handler(user: User | None = Depends(get_optional_user)):
    ...

# 管理员
@router.get("/admin")
async def handler(admin: User = Depends(require_admin)):
    ...
```

## HTTP API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/auth/me` | 获取当前用户信息 | 登录 |
| PATCH | `/api/v1/auth/me` | 更新个人信息 | 登录 |
| POST | `/api/v1/auth/sync` | 从 Auth0 同步信息 | 登录 |
| GET | `/api/v1/auth/users` | 列出用户 | admin |
| GET | `/api/v1/auth/users/{id}` | 获取指定用户 | admin |

## User 数据模型

```python
User:
    id: str              # 内部 ID（user_xxxx）
    auth0_id: str        # Auth0 sub
    email: str
    nickname: str
    avatar: str
    role: str            # user | admin
    permissions: list
    quota: int           # 配额
    subscription: str    # free | pro | enterprise
    preferences: dict    # 用户偏好
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime
```

## 配置项（.env）

| 变量 | 说明 | 必填 |
|------|------|------|
| `AUTH0_DOMAIN` | Auth0 租户域名 | 是 |
| `AUTH0_AUDIENCE` | API Audience | 是 |
| `AUTH0_CLIENT_ID` | 应用 Client ID | 是 |
| `AUTH0_ALGORITHMS` | 签名算法 | 否（默认 RS256） |
| `AUTH_USER_COLLECTION` | MongoDB 集合名 | 否（默认 users） |

## 与其他模块的集成

- **chat**：Session 关联 `user_id`，创建/查询时自动注入当前用户，实现数据隔离
- **prompt**：用户创建的 prompt 可关联 `user_id`，仅本人可见可改
