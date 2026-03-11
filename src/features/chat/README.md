# Chat 会话管理模块

提供 session 隔离的多轮对话，内置上下文持久化（MongoDB + 内存缓存）和 token 截断。

## 模块结构

```
features/chat/
├── configs/config.py              # 集合名、缓存大小、token 上限
├── models/models.py               # Session、ChatMessage
├── providers/cache.py             # 内存 LRU 缓存
├── repositories/repository.py     # MongoDB CRUD
├── services/
│   ├── session.py                 # SessionManager
│   └── service.py                 # ChatService（核心）
├── api/routes.py                  # HTTP 路由
└── README.md
```

## 使用方式

### HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/sessions` | 创建会话 |
| GET | `/api/v1/chat/sessions` | 列出会话 |
| GET | `/api/v1/chat/sessions/{id}` | 获取会话详情 |
| PATCH | `/api/v1/chat/sessions/{id}` | 更新会话设置 |
| DELETE | `/api/v1/chat/sessions/{id}` | 删除会话 |
| POST | `/api/v1/chat/sessions/{id}/messages` | 发送消息 |
| GET | `/api/v1/chat/sessions/{id}/messages` | 获取历史消息 |

### 后端内部调用

```python
from core.mongodb import get_database
from features.chat import create_chat_service

db = get_database()
service = create_chat_service(db)

# 创建会话
session = await service.create_session(
    title="视频处理助手",
    system_prompt="你是一个视频处理专家",
    use_tools=True,
)

# 发送消息（自动管理上下文 + tool calling）
resp = await service.send_message(session.id, "帮我看看这个视频的信息")
print(resp.content)
print(f"消耗 token: {resp.input_tokens} + {resp.output_tokens}")

# 继续对话（上下文自动延续）
resp = await service.send_message(session.id, "把它和另一个视频拼接起来")
```

## 核心流程

```
send_message(session_id, content)
    │
    ├─ 1. 获取 session 元数据
    ├─ 2. 加载历史消息（缓存优先，miss 查 DB）
    ├─ 3. 追加 user 消息 → 写 DB + 更新缓存
    ├─ 4. 构建 API 消息列表 → token 截断
    ├─ 5. 调用 Claude（含 tool calling 自动循环）
    ├─ 6. 保存 assistant 消息 → 写 DB + 更新缓存
    └─ 7. 更新 session token 统计
```

## 上下文管理

- **内存缓存**：LRU 策略缓存活跃 session 的消息列表，避免频繁查 DB
- **MongoDB 持久化**：所有消息持久存储，支持多端同步和历史回溯
- **token 截断**：消息历史超出 `max_context_tokens` 时，从最早的消息开始丢弃

## 配置项（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CHAT_SESSION_COLLECTION` | session 集合名 | chat_sessions |
| `CHAT_MESSAGE_COLLECTION` | message 集合名 | chat_messages |
| `CHAT_CACHE_SIZE` | LRU 缓存大小 | 50 |
| `CHAT_MAX_CONTEXT_TOKENS` | 上下文 token 上限 | 100000 |
