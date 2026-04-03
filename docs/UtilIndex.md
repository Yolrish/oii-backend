# 会话需求记录

## 项目前提

- **技术栈**: FastAPI + MongoDB + Auth0
- **主要用途**: AI 服务后端
- **模块分层**:
  - `packages/`：基础能力模块（独立、可复用、无业务逻辑）
  - `features/`：业务编排模块（组合 packages，含持久化和 HTTP API）
- **模块要求**:
  - 每个功能模块需**独立**（可单独维护、低耦合）
  - 每个功能模块需具备**对外接口**（可被其他模块或外部调用）

## .env 加载规范

- **启动时**：`import load_env` 将项目根 `.env` 加载到 `os.environ`
- **优先级**：内存（os.environ）> 模块包 `.env` > 默认值
- **新模块**：在 config 中调用 `load_module_env(__file__)` 后使用 `os.getenv()`

## tool_call 规范

- `packages/tool_call` 是纯粹的工具注册 + 执行模块，**不对外暴露 HTTP 接口**
- 所有工具来源（项目内函数、MCP、Skill）统一通过 `register_tool` 注册
- 内置工具放在 `tool_call/builtin/` 下

## prompt 规范

- `features/prompt` 统一管理三种来源的 prompt
- **builtin**：代码内置，不可通过 API 删改
- **user**：用户通过 API 创建，存 MongoDB，可 CRUD，同名覆盖 builtin
- **external**：第三方平台（预留 `ExternalPromptProvider` 接口）
- **system_guard**：安全底线 prompt，最高优先级，始终注入 system prompt 最前面

## SSE 事件规范

- 事件类型定义在 `packages/claude/models/sse.py`
- 6 种事件：`message_start`、`content_delta`、`tool_use_start`、`tool_use_result`、`message_end`、`error`
- chat API 通过 `stream=true` 参数启用

## Twitter/X API 规范

- `packages/twitter` 封装 X (Twitter) 官方 API v2
- **认证方式**：OAuth 1.0a（发推、点赞等写操作）、Bearer Token（搜索、查询等只读操作）
- **主要功能**：发送/删除推文、搜索推文、查询用户、时间线、点赞/转推、关注/取关
- **环境变量**：`TWITTER_API_KEY`、`TWITTER_API_SECRET`、`TWITTER_ACCESS_TOKEN`、`TWITTER_ACCESS_TOKEN_SECRET`、`TWITTER_BEARER_TOKEN`
- 使用 `httpx` 作为异步 HTTP 客户端，OAuth 1.0a 签名基于 RFC 5849 内置实现

## 认证规范

- `features/auth` 基于 Auth0 SPA 模式（Authorization Code + PKCE）
- 前端通过 auth0-spa-js 登录，后端只验证 Token
- 认证依赖：`get_current_user`、`get_optional_user`、`require_admin`
- chat session 关联 `user_id`，实现用户数据隔离

## API 安全审计

### 已禁用的路由（从 router.py 注释掉）

| 模块 | 原因 | 恢复条件 |
|------|------|---------|
| `users.py` | 脚手架演示，认证仅检查 `X-User-Id` 请求头（可伪造） | 迁移为 Auth0 认证后启用 |
| `items.py` | 脚手架演示，大部分端点无认证 | 迁移为 Auth0 认证后启用 |
| `workflow` | 全部端点无认证，`/run` 可通过 shell handler 执行任意代码 | 添加认证 + 权限控制后启用 |

### 已补全认证的路由

- **chat**：`get/patch/delete /sessions/{id}` 和 `post/get /sessions/{id}/messages` 增加 `get_current_user` + `user_id` 归属校验（403）
- **prompt**：`post/put/delete` 写操作增加 `get_current_user`；读操作（list/get/render）保持公开
