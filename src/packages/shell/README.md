# Shell 命令执行模块

提供系统命令行执行能力，支持 Web 后端高并发场景。

## 特性

- ⚡ **异步支持** - 提供同步和异步 API
- 🔄 **并发控制** - Semaphore 限制同时执行的命令数
- 📺 **实时输出** - 支持回调和生成器两种流式输出模式
- 🧵 **线程池** - 同步方法可在线程池中异步执行
- 🔒 **无状态设计** - 天然支持并发调用
- ⌨️ **预写 stdin** - 支持 `stdin_input`，用于可预知选项的“伪交互”命令（如 npx 选第一项）

## 快速开始

```python
from packages.shell import run, run_async

# 同步执行
result = run("git status")
print(result.stdout)

# 异步执行
result = await run_async("git status")
print(result.stdout)
```

### FastAPI 中使用

```python
from fastapi import FastAPI
from packages.shell import create_shell_service

app = FastAPI()
shell = create_shell_service(max_concurrent=10)

@app.get("/run")
async def run_command(cmd: str):
    result = await shell.run_async(cmd, timeout=30)
    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

@app.get("/stream")
async def stream_command(cmd: str):
    from fastapi.responses import StreamingResponse
    
    async def generate():
        async for line in shell.stream_async(cmd):
            yield f"data: {line.content}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## API

### 创建服务

```python
from packages.shell import create_shell_service, ShellConfig

# 方式1：默认配置
service = create_shell_service()

# 方式2：自定义配置
config = ShellConfig(timeout=600, raise_on_error=True)
service = create_shell_service(
    config=config,
    max_concurrent=10,      # 最大并发数
    thread_pool_size=4,     # 线程池大小
)

# 方式3：使用默认单例
from packages.shell import get_default_service
service = get_default_service()
```

### 执行命令

```python
# 同步执行
result = service.run("echo hello")

# 异步执行（推荐在 Web 后端使用）
result = await service.run_async("echo hello")

# 在线程池中执行同步方法
result = await service.run_in_thread("echo hello")
```

### 实时输出

**回调模式：**

```python
def on_output(line: str):
    print(f"[实时] {line}", end="")

# 同步
result = service.run("pip install requests", on_stdout=on_output)

# 异步
result = await service.run_async("pip install requests", on_stdout=on_output)
```

**生成器模式（同步）：**

```python
for line in service.stream("npm install"):
    print(f"[{line.stream_type}] {line.content}")
```

**异步生成器模式：**

```python
async for line in service.stream_async("npm install"):
    print(f"[{line.stream_type}] {line.content}")
```

### 批量执行

```python
# 顺序执行
results = service.run_many(["echo 1", "echo 2", "echo 3"])

# 异步顺序执行
results = await service.run_many_async(commands, concurrent=False)

# 异步并发执行
results = await service.run_many_async(commands, concurrent=True)
```

### 需输入的命令（stdin_input）

对选项固定、可预知的命令，可用 `stdin_input` 在启动时一次性写入 stdin（如 `"1\n"` 表示选第一项并回车）：

```python
# 预写选择，相当于用户输入 1 并回车
result = await service.run_async("npx some-prompt", stdin_input="1\n")
```

> **说明**：真正的 TTY 多轮交互（如动态菜单）不支持；建议优先用工具的非交互参数（如 `npx --yes`）。

## 同步方法 vs 异步方法

| 同步方法 | 异步方法 | 说明 |
|----------|----------|------|
| `run()` | `run_async()` | 执行命令 |
| `stream()` | `stream_async()` | 流式执行 |
| `run_many()` | `run_many_async()` | 批量执行 |
| - | `run_in_thread()` | 线程池执行同步方法 |

> ⚠️ **注意**：在 FastAPI 等异步框架中，请使用 `*_async()` 方法，避免阻塞事件循环。

## 并发控制

```python
# 创建服务时指定最大并发数
service = create_shell_service(max_concurrent=10)

# 即使 100 个请求同时调用，也只会同时执行 10 个命令
results = await asyncio.gather(
    service.run_async("task1"),
    service.run_async("task2"),
    # ... 更多任务会排队
)
```

> **注意**：并发控制只对 `*_async()` 方法生效。

## 结果对象

```python
@dataclass
class CommandResult:
    success: bool           # return_code == 0
    return_code: int        # 返回码
    stdout: str             # 标准输出
    stderr: str             # 标准错误
    command: str            # 执行的命令
    cwd: str                # 工作目录
    execution_time: float   # 执行耗时（秒）
    timed_out: bool         # 是否超时
    
    # 便捷属性
    output: str             # stdout + stderr
    stdout_lines: list      # stdout 按行分割
    stderr_lines: list      # stderr 按行分割
```

使用示例：

```python
result = await service.run_async("git status")

if result.success:
    print(result.stdout)
else:
    print(f"Error (code={result.return_code}): {result.stderr}")

# 支持 bool 判断
if result:
    print("Success!")
```

## 配置项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `timeout` | 300 | 超时时间（秒），0 表示无限制 |
| `encoding` | utf-8 | 输出编码 |
| `cwd` | None | 默认工作目录 |
| `env` | None | 环境变量 |
| `raise_on_error` | False | 失败时是否抛出异常 |
| `max_concurrent` | 10 | 最大并发数（服务层） |
| `thread_pool_size` | 4 | 线程池大小（服务层） |

执行方法均支持可选参数：`cwd`、`env`、`timeout`、`on_stdout`、`on_stderr`、`stdin_input`。

### 环境变量

| 变量 | 说明 |
|------|------|
| `SHELL_TIMEOUT` | 默认超时时间 |
| `SHELL_ENCODING` | 默认编码 |

## 异常处理

```python
from packages.shell import ShellError, ShellTimeoutError, ShellExecutionError

# 方式1：检查结果
result = await service.run_async("some_command")
if result.timed_out:
    print("命令超时")
elif not result.success:
    print(f"执行失败: {result.stderr}")

# 方式2：配置抛出异常
config = ShellConfig(raise_on_error=True)
service = create_shell_service(config)

try:
    result = await service.run_async("invalid_command")
except ShellTimeoutError as e:
    print(f"超时: {e.command}")
except ShellExecutionError as e:
    print(f"失败: {e.return_code}")
```

## 资源管理

```python
# 使用上下文管理器
async with create_shell_service() as service:
    result = await service.run_async("echo hello")

# 或手动关闭
service = create_shell_service()
try:
    result = await service.run_async("echo hello")
finally:
    service.close()
```

## 目录结构

```
shell/
├── __init__.py          # 模块入口
├── configs/
│   └── config.py        # ShellConfig 配置类
├── models/
│   └── models.py        # CommandResult, StreamLine 等
├── providers/
│   ├── executor.py      # ShellExecutor 核心执行器
│   └── exceptions.py    # 异常定义
├── services/
│   └── service.py       # ShellService 服务层
├── example.py           # 使用示例
└── README.md
```

## 使用示例

运行示例：

```bash
cd src
python -m packages.shell.example
```
