# Agent + Tool Call + MCP/Skill 集成方案

## 当前状态

| 模块 | 层级 | 状态 |
|------|------|------|
| `packages/tool_call` | 基础能力 | 已实现 — 工具注册 + 执行 |
| `packages/claude` | 基础能力 | 已实现 — Claude SDK 封装（同步/异步/流式 + tool calling） |
| `features/auth` | 业务编排 | 已实现 — Auth0 认证 + 用户管理 + 数据隔离 |
| `features/chat` | 业务编排 | 已实现 — 会话管理 + 上下文 + SSE 流式对话 |
| `features/prompt` | 业务编排 | 已实现 — Prompt 多来源管理 + 安全底线 |
| MCP 桥接 | 基础能力 | 待实现 — 独立 package，封装后 register_tool |
| Skill 适配 | 基础能力 | 待实现 — 独立 package，封装后 register_tool |

## 架构关系

```
features/auth          ← 用户认证（Auth0 JWT）
features/chat          ← 会话管理 + SSE 流式对话（需认证）
  ├─ features/prompt   ← Prompt 渲染（安全底线 + 业务 prompt）
  ├─ packages/claude   ← LLM 调用（流式 + tool calling 循环）
  │    └─ packages/tool_call  ← 工具执行
  │         ├─ builtin/shell_tools   ← Shell 命令
  │         ├─ builtin/ffmpeg_tools  ← 视频处理
  │         └─ (未来) mcp_bridge / skill 注册的工具
  └─ core/mongodb      ← 持久化
```

## MCP / Skill 集成方式

作为独立 package 实现，内部封装通信逻辑，对外只调 `register_tool`：

```python
from packages.tool_call import register_tool

@register_tool(name="mcp_xxx", description="...", ...)
async def mcp_xxx(**kwargs):
    ...
```
