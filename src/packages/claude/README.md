# Claude 对话模块

基于 Anthropic SDK 的对话服务，支持普通对话和 Tool Calling。

## 模块结构

```
packages/claude/
├── __init__.py
├── configs/
│   └── config.py        # API Key、模型、温度等
├── models/
│   └── messages.py      # Message、ChatResponse 等
├── providers/
│   └── client.py        # Anthropic SDK 封装
├── services/
│   └── service.py       # 对话服务（含 tool calling 循环）
└── README.md
```

## 使用方式

### 简单对话

```python
from packages.claude import create_claude_service

service = create_claude_service()
resp = await service.chat("你好，介绍一下你自己")
print(resp.content)
```

### 带工具的对话

自动从 `tool_call` 模块获取已注册的工具，LLM 按需调用：

```python
resp = await service.chat("帮我看看当前目录有哪些文件", use_tools=True)
print(resp.content)
print(f"调用了 {len(resp.tool_calls_history)} 次工具")
```

### 多轮对话

```python
messages = [
    {"role": "user", "content": "我想拼接两个视频"},
]
resp = await service.chat_with_history(messages, use_tools=True)

# 继续对话
messages.append({"role": "assistant", "content": resp.content})
messages.append({"role": "user", "content": "请先检查它们是否兼容"})
resp = await service.chat_with_history(messages, use_tools=True)
```

### 同步调用

```python
resp = service.chat_sync("你好")
```

### 自定义配置

```python
from packages.claude import ClaudeConfig, create_claude_service

config = ClaudeConfig(
    api_key="sk-xxx",
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    system_prompt="你是一个视频处理助手",
    max_tool_rounds=5,
)
service = create_claude_service(config)
```

## 配置项（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CLAUDE_API_KEY` | Anthropic API Key | 必填 |
| `CLAUDE_MODEL` | 模型名称 | claude-sonnet-4-20250514 |
| `CLAUDE_MAX_TOKENS` | 最大输出 token | 4096 |
| `CLAUDE_TEMPERATURE` | 温度 | 0.7 |
| `CLAUDE_SYSTEM_PROMPT` | 系统提示词 | 空 |
| `CLAUDE_MAX_TOOL_ROUNDS` | Tool calling 最大轮数 | 10 |
| `CLAUDE_TIMEOUT` | 请求超时（秒） | 120 |
| `CLAUDE_BASE_URL` | 自定义 API 地址 | 空 |

## Tool Calling 流程

```
用户消息 → Claude API（带 tools）
    ↓
Claude 返回 tool_use → 执行 tool_call 模块中的工具 → 结果回传
    ↓
Claude 继续推理 → 可能再次调用工具 → ...
    ↓
Claude 返回最终回复（stop_reason=end_turn）
```

最多循环 `max_tool_rounds` 轮，防止无限调用。
