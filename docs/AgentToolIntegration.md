# Agent 聊天 + 函数调用 + MCP/Skill 集成实现方案

> **已实现**：`packages/agent` 模块提供工具注册、执行及 MCP/Skill 扩展接口。见下方「已实现部分」。

## 一、整体架构

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│  用户聊天   │────▶│                    Agent 核心                       │
└─────────────┘     │  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  │
                   │  │ LLM 调用   │─▶│ Tool 选择    │─▶│ 执行函数    │  │
                   │  │ (OpenAI/   │  │ (function   │  │ 或 MCP/Skill│  │
                   │  │  Claude)   │  │  calling)   │  │             │  │
                   │  └────────────┘  └─────────────┘  └─────────────┘  │
                   └──────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
            │ 项目内函数   │   │ MCP 服务器   │   │ Skill 能力    │
            │ (packages/*) │   │ (外部工具)   │   │ (Cursor 等)   │
            └───────────────┘   └───────────────┘   └───────────────┘
```

**核心流程**：用户消息 → LLM 推理 → 若需工具则返回 tool_calls → 执行对应函数/MCP/Skill → 结果回传 LLM → 生成最终回复

---

## 二、已实现部分（packages/agent）

| 组件 | 路径 | 说明 |
|------|------|------|
| 工具注册表 | `tools/registry.py` | `register_tool` 装饰器、`get_tools_for_llm`、`execute_tool`、`execute_tool_by_name`、`get_all_tools` |
| MCP/Skill 扩展 | `tools/extensions.py` | `BaseToolProvider`、`MCPToolProvider`、`SkillToolProvider`、`register_mcp_provider`、`register_skill_provider` |
| 内置工具 | `tools/builtin/shell_tools.py` | `run_shell_command` 示例 |
| API | `api/routes.py` | `GET /agent/tools`、`GET /agent/tools/local`、`POST /agent/tools/execute` |

**扩展 MCP**：实现 `MCPToolProvider` 子类，实现 `list_tools()` 与 `call_tool()`，调用 `register_mcp_provider(provider)`。

**扩展 Skill**：实现 `SkillToolProvider` 子类，同上，调用 `register_skill_provider(provider)`。

---

## 三、实现步骤（LLM 聊天部分待实现）

### 2.1 新建 agent 包结构

```
src/packages/agent/
├── __init__.py
├── configs/
│   └── config.py          # API Key、模型等
├── models/
│   └── messages.py       # 消息结构
├── providers/
│   ├── __init__.py
│   ├── llm.py            # LLM 抽象（OpenAI/Claude 统一接口）
│   └── tool_registry.py  # 工具注册表
├── services/
│   └── chat_service.py   # 聊天 + 工具循环
├── tools/                # 项目内工具（可被 agent 调用）
│   ├── __init__.py
│   └── registry.py       # 注册 packages 下的函数
└── api/
    └── routes.py         # POST /chat 等
```

### 2.2 工具定义格式（兼容 OpenAI / Anthropic）

LLM 的 function calling 需要 JSON Schema 描述工具：

```python
# 工具定义示例
{
    "type": "function",
    "function": {
        "name": "run_shell_command",
        "description": "在服务器上执行 shell 命令",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
                "timeout": {"type": "integer", "description": "超时秒数"}
            },
            "required": ["command"]
        }
    }
}
```

### 2.3 项目内函数注册机制

**思路**：各 packages 通过装饰器或显式注册，将可调用函数暴露给 agent。

```python
# packages/agent/tools/registry.py
from typing import Callable, Dict, Any, List
import inspect
import json

_tools: Dict[str, dict] = {}      # name -> OpenAI 格式的 tool 定义
_handlers: Dict[str, Callable] = {}  # name -> 实际函数

def register_tool(
    name: str,
    description: str,
    parameters: dict,  # JSON Schema
):
    def decorator(fn: Callable):
        _tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {"type": "object", "properties": parameters, "required": [...]}
            }
        }
        _handlers[name] = fn
        return fn
    return decorator

def get_tools_for_llm() -> List[dict]:
    """返回 LLM API 所需的 tools 列表"""
    return list(_tools.values())

def execute_tool(name: str, arguments: dict) -> Any:
    """根据 name 执行对应函数"""
    fn = _handlers.get(name)
    if not fn:
        raise ValueError(f"Unknown tool: {name}")
    return fn(**arguments)
```

**packages 中的使用**：

```python
# packages/shell/tools.py（新建）
from packages.agent.tools.registry import register_tool

@register_tool(
    name="run_shell_command",
    description="在服务器上执行 shell 命令，返回 stdout/stderr",
    parameters={
        "command": {"type": "string", "description": "要执行的命令"},
        "timeout": {"type": "integer", "description": "超时秒数，默认 60"}
    }
)
def run_shell_command(command: str, timeout: int = 60) -> dict:
    from packages.shell import ShellService
    svc = ShellService()
    result = svc.run_sync(command, timeout=timeout)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
```

### 2.4 聊天 + 工具循环（Agent 核心）

```python
# packages/agent/services/chat_service.py
async def chat_with_tools(
    messages: List[dict],
    tools: List[dict],
    max_tool_rounds: int = 5,
) -> dict:
    """
    多轮对话：若 LLM 返回 tool_calls，则执行并追加结果，再继续调用 LLM。
    """
    current_messages = list(messages)
    for _ in range(max_tool_rounds):
        response = await llm_client.chat(
            messages=current_messages,
            tools=tools,
        )
        # 若无 tool_calls，直接返回
        if not response.get("tool_calls"):
            return {"message": response["content"], "finish_reason": "stop"}

        # 有 tool_calls：逐个执行，构造 tool 结果消息
        tool_results = []
        for tc in response["tool_calls"]:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            result = execute_tool(name, args)  # 或调用 MCP/Skill
            tool_results.append({
                "tool_call_id": tc["id"],
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False)
            })

        # 追加 assistant 消息 + tool 结果，继续下一轮
        current_messages.append({"role": "assistant", "content": response["content"], "tool_calls": response["tool_calls"]})
        current_messages.extend(tool_results)

    return {"message": "达到最大工具调用轮数", "finish_reason": "max_tool_rounds"}
```

### 2.5 MCP 集成

**方式一：MCP Client 作为工具源**

使用 `mcp` Python SDK 连接 MCP 服务器，将其暴露的 tools 转为上述格式，并入 `get_tools_for_llm()`。

```python
# 依赖：pip install mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def load_mcp_tools(server_command: List[str]) -> List[dict]:
    """连接 MCP 服务器，获取其 tools 列表并转为 OpenAI 格式"""
    server_params = StdioServerParameters(command=server_command)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            # 将 MCP Tool 转为 OpenAI function 格式
            return [mcp_tool_to_openai(t) for t in tools_result.tools]

async def call_mcp_tool(server_command: List[str], tool_name: str, arguments: dict) -> Any:
    """调用 MCP 服务器的某个 tool"""
    async with stdio_client(...) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result
```

**方式二：Streamable HTTP**

若 MCP 服务器以 HTTP 运行，可用 `StreamableHTTPTransport` 连接。

```python
from mcp.client.sse import sse_client  # 或 streamable_http
# 见 MCP Python SDK 文档
```

### 2.6 Skill 集成（Cursor 风格）

Skill 本质是「预定义能力描述 + 调用方式」。两种做法：

**A. Skill 即 MCP**：将 Skill 实现为 MCP 服务器，通过 MCP Client 接入。

**B. Skill 即本地函数**：在项目中实现，用 `register_tool` 注册，与 packages 内函数一致。

若 Skill 来自外部（如 Cursor 的 `.cursor/skills/`），可：
- 解析 Skill 的 SKILL.md 获取能力描述
- 若其提供 HTTP/CLI 接口，封装为 `register_tool` 的 handler
- 或通过 MCP 桥接（若 Skill 端支持 MCP）

### 2.7 统一工具聚合

```python
# packages/agent/services/chat_service.py
async def get_all_tools() -> List[dict]:
    """聚合：项目内工具 + MCP 工具 + Skill 工具"""
    tools = list(get_tools_for_llm())  # 项目内
    # 若配置了 MCP 服务器
    if mcp_command := config.mcp_server_command:
        mcp_tools = await load_mcp_tools(mcp_command)
        tools.extend(mcp_tools)
    # 若配置了 Skill 端点，可在此追加
    return tools
```

执行时根据 `tool_call.name` 判断来源：
- 若在 `_handlers` 中 → 本地执行
- 若来自 MCP → `call_mcp_tool(...)`
- 若来自 Skill → 调用对应 Skill 适配器

---

## 三、技术选型建议

| 组件 | 推荐 | 说明 |
|------|------|------|
| LLM | OpenAI / Anthropic | 原生 function calling，接口成熟 |
| 统一接口 | LiteLLM | 可统一多模型，减少适配 |
| MCP | mcp Python SDK | 官方实现，支持 stdio/SSE/HTTP |
| 工具注册 | 自研 registry | 与 packages 解耦，各模块按需注册 |

---

## 四、配置项（.env）

```env
# Agent
AGENT_LLM_PROVIDER=openai   # openai | anthropic
AGENT_OPENAI_API_KEY=
AGENT_OPENAI_MODEL=gpt-4o
AGENT_ANTHROPIC_API_KEY=
AGENT_ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
AGENT_MCP_SERVER_COMMAND=   # 可选，如 "npx -y @modelcontextprotocol/server-filesystem"
AGENT_MAX_TOOL_ROUNDS=5
```

---

## 五、API 设计示例

```
POST /api/v1/agent/chat
{
  "messages": [{"role": "user", "content": "帮我执行 ls -la"}],
  "stream": false
}

Response:
{
  "message": "已执行 ls -la，结果如下：...",
  "tool_calls": [...],  // 可选，本次用到的工具
  "finish_reason": "stop"
}
```

---

## 六、实现顺序建议

1. **工具注册表**：`registry.py` + 装饰器，先注册 1～2 个简单函数
2. **LLM 封装**：封装 OpenAI/Claude 的 chat + tools 调用
3. **聊天循环**：实现 `chat_with_tools`，支持多轮 tool_calls
4. **API 路由**：`POST /agent/chat`，接入 FastAPI
5. **MCP 集成**：按需接入 1 个 MCP 服务器验证
6. **Skill 适配**：根据实际 Skill 形态做适配层

---

## 七、与现有 Workflow 的关系

- **Workflow**：预定义步骤的编排执行（AI 可生成 WorkflowSpec）
- **Agent**：对话式、按需调用工具

可结合：Agent 在对话中调用「创建工作流」「执行工作流」等工具，将 `WorkflowService` 作为工具之一注册，实现「对话驱动工作流」。
