# Tool-Call 模块

统一的工具注册与执行模块。仅供项目内部调用，不对外暴露 HTTP 接口。

## 模块结构

```
packages/tool_call/
├── __init__.py        # 对外导出，导入 builtin 触发内置工具注册
├── registry.py        # 核心：注册、列出、执行
├── builtin/           # 内置工具
│   ├── __init__.py
│   └── shell_tools.py # Shell 命令工具
└── README.md
```

## 核心 API

| 函数 | 说明 |
|------|------|
| `register_tool(name, description, parameters, required)` | 装饰器，注册函数为工具 |
| `get_tools_for_llm()` | 返回所有工具的 OpenAI 格式列表 |
| `execute_tool(name, arguments)` | 同步执行工具 |
| `execute_tool_async(name, arguments)` | 异步执行（自动适配同步/异步 handler） |
| `has_tool(name)` | 检查工具是否已注册 |
| `unregister_tool(name)` | 移除工具 |

## 注册工具

用 `@register_tool` 装饰器注册，`parameters` 为 JSON Schema 格式：

```python
from packages.tool_call import register_tool

@register_tool(
    name="my_tool",
    description="工具用途描述",
    parameters={
        "arg1": {"type": "string", "description": "参数说明"},
        "count": {"type": "integer", "description": "数量，默认 10"},
    },
    required=["arg1"],
)
def my_tool(arg1: str, count: int = 10) -> dict:
    return {"result": arg1, "count": count}
```

异步函数同样支持：

```python
@register_tool(
    name="async_tool",
    description="异步工具示例",
    parameters={"url": {"type": "string", "description": "请求地址"}},
    required=["url"],
)
async def async_tool(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        resp = await session.get(url)
        return {"status": resp.status}
```

## 调用工具

```python
from packages.tool_call import execute_tool, execute_tool_async

# 同步
result = execute_tool("my_tool", {"arg1": "hello"})

# 异步（推荐，自动适配同步/异步 handler）
result = await execute_tool_async("my_tool", {"arg1": "hello"})
```

## 获取工具列表

返回 OpenAI function calling 格式，可直接传给 LLM：

```python
from packages.tool_call import get_tools_for_llm

tools = get_tools_for_llm()
# [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]
```

## 添加内置工具

在 `builtin/` 下新建文件，用 `@register_tool` 注册，然后在 `builtin/__init__.py` 中导入：

```python
# builtin/my_tools.py
from ..registry import register_tool

@register_tool(name="xxx", description="...", ...)
def xxx(...):
    ...
```

```python
# builtin/__init__.py
from .shell_tools import *  # noqa: F401, F403
from .my_tools import *     # noqa: F401, F403  ← 新增
```

## 其他模块集成

MCP、Skill 等外部能力作为独立 package 实现，内部封装通信逻辑后，
通过 `register_tool` 将能力注册为普通工具即可，对本模块完全透明。
