# AI Backend

基于 FastAPI + MongoDB 的 AI 后端服务。

## 技术栈

- **框架**: FastAPI + Uvicorn
- **数据库**: MongoDB (Motor 异步驱动)
- **认证**: Auth0 (JWT + JWKS)
- **依赖管理**: uv
- **LLM**: Anthropic Claude（支持 SSE 流式输出）
- **日志**: OpenSearch
- **视频处理**: FFmpeg

## 快速开始

```bash
# 安装依赖
uv sync

# 复制配置
cp .env.example .env

# 启动开发服务器
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 项目结构

```
src/
├── main.py              # 应用入口，lifespan 管理
├── load_env.py          # 统一 .env 加载 + load_module_env 工具
├── api/v1/              # HTTP 路由层
│   ├── router.py        # 路由聚合
│   └── endpoints/       # health, users, items
├── core/                # 核心基础设施
│   ├── config.py        # MongoDB 配置
│   └── mongodb.py       # MongoDB 连接管理
├── packages/            # 基础能力层（独立、可复用、无业务逻辑）
│   ├── claude/          # Claude SDK 封装（同步/异步/流式）
│   ├── ffmpeg/          # 视频处理（信息、拼接、混音）
│   ├── log/             # 日志服务（OpenSearch）
│   ├── shell/           # Shell 命令执行
│   └── tool_call/       # 工具注册与执行（仅内部调用）
├── features/            # 业务编排层（组合 packages，含 DB + HTTP API）
│   ├── auth/            # 用户系统（Auth0 认证 + 用户管理）
│   ├── chat/            # 会话管理 + 上下文持久化 + SSE 流式对话
│   ├── prompt/          # Prompt 管理（builtin + user DB + 第三方预留）
│   └── workflow/        # 动态工作流引擎
├── repositories/        # 数据仓储
├── schemas/             # Pydantic 请求/响应模型
└── services/            # 通用业务逻辑
```

## 模块分层

### packages — 基础能力

独立、可复用、不含业务逻辑：

| 模块 | 用途 | 对外暴露 |
|------|------|----------|
| **claude** | Claude API 封装（含流式 + tool calling） | Service API |
| **ffmpeg** | 视频信息、拼接、混音 | Service API |
| **log** | 多 Provider 日志写入 | Service API |
| **shell** | 系统命令执行 | Service API |
| **tool_call** | 工具注册与执行 | 仅内部调用 |

### features — 业务编排

组合 packages，包含 DB 持久化和 HTTP API：

| 模块 | 用途 | 依赖 |
|------|------|------|
| **auth** | 用户认证与管理（Auth0 JWT 验证） | Auth0 + MongoDB |
| **chat** | 会话管理、上下文持久化、SSE 流式对话 | auth + claude + tool_call + prompt + MongoDB |
| **prompt** | Prompt 统一管理（builtin + user + 第三方） | MongoDB |
| **workflow** | Step 串行 + Task 并行工作流 | MongoDB |

## 核心流程

```
前端 Auth0 登录 → 获取 Access Token
    → 请求后端 API（Bearer Token）
    → features/auth 验证 Token + 同步用户
    → features/chat 发消息（stream=true）
        → session 管理 + 上下文加载 + token 截断
        → features/prompt 渲染 system prompt（安全底线 + 业务 prompt）
        → packages/claude 流式调用 Claude API
            → packages/tool_call 执行工具（若 Claude 请求 tool_use）
        → SSE 实时推送：content_delta / tool_use_start / tool_use_result / message_end
    → 保存消息到 MongoDB + 更新缓存
```

## .env 加载机制

- 启动时 `load_env.py` 将项目根 `.env` 加载到 `os.environ`
- 各模块通过 `load_module_env(__file__)` 补充包级 `.env`（不覆盖）
- 优先级：内存 > 模块 `.env` > 默认值

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 常用命令

```bash
# 添加依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>

# 更新依赖
uv lock --upgrade && uv sync
```
