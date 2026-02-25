# Log 日志服务

支持多 Provider 的统一日志写入服务，支持 Web 后端高并发场景。

## 特性

- 🔌 **多 Provider 架构** - 支持同时写入多个日志后端
- 🎯 **单例模式** - 全局统一的日志服务入口
- 📦 **批量写入** - 支持单条和批量日志写入
- 🔧 **灵活配置** - 支持代码配置和环境变量
- 📊 **多索引** - 支持按业务分类存储到不同索引
- ⚡ **异步支持** - 提供异步 API，适合 FastAPI 等框架
- 🔒 **线程安全** - 写入操作使用锁保护

## 快速开始

### 最简方式

```python
from packages.log import create_default_log_service

# 创建服务（自动注册 OpenSearch Provider）
service = create_default_log_service()
service.init()

# 写入日志（同步）
service.info("User logged in", service="auth")
service.warn("High memory usage", service="system")
service.error("Connection failed", service="api", status_code=500)
```

### FastAPI 中使用（推荐异步 API）

```python
from fastapi import FastAPI
from packages.log import create_default_log_service

app = FastAPI()
log = create_default_log_service()
log.init()

@app.get("/api/users")
async def get_users():
    await log.info_async("Fetching users", service="api")
    # ... 业务逻辑
    return {"users": []}

@app.exception_handler(Exception)
async def error_handler(request, exc):
    await log.error_async(str(exc), service="api", status_code=500)
    return {"error": str(exc)}
```

### 手动配置

```python
from packages.log import LogService, OpenSearchProvider, OpenSearchConfig

service = LogService()

# 自定义配置
config = OpenSearchConfig(
    host="https://your-host/opensearch",
    username="admin",
    password="password",
    index_name="logs-backend",
)

# 注册并初始化
service.register_provider(OpenSearchProvider(config))
service.init()

# 写入
await service.info_async("Hello", service="api")
```

## 日志写入

### 同步方法 vs 异步方法

| 同步方法 | 异步方法 | 说明 |
|----------|----------|------|
| `info()` | `info_async()` | 写入普通日志 |
| `warn()` | `warn_async()` | 写入警告日志 |
| `error()` | `error_async()` | 写入错误日志 |
| `log()` | `log_async()` | 写入指定级别日志 |
| `bulk_log()` | `bulk_log_async()` | 批量写入 |

> ⚠️ **建议**：在 FastAPI 等异步框架中使用 `*_async()` 方法，避免阻塞事件循环。

### 基础写入

```python
# 同步写入
service.info("普通日志", service="api")
service.warn("警告日志", service="api")
service.error("错误日志", service="api")

# 异步写入（推荐）
await service.info_async("普通日志", service="api")
await service.warn_async("警告日志", service="api")
await service.error_async("错误日志", service="api")

# 带用户信息
await service.info_async("User action", service="api", user="john", user_id="12345")

# 带 HTTP 信息
await service.error_async("Request failed", service="api", status_code=500, ip="192.168.1.1")

# 带扩展数据
await service.info_async("Order created", service="order", metadata={"order_id": "ORD001", "amount": 99.9})
```

### 批量写入

```python
from packages.log import LogEntry, LogLevel

entries = [
    LogEntry(message="Log 1", service="api"),
    LogEntry(message="Log 2", service="api", level=LogLevel.WARN),
    LogEntry(message="Log 3", service="api", user="john"),
]

# 同步
results = service.bulk_log(entries)

# 异步（推荐）
results = await service.bulk_log_async(entries)
# 返回: {"opensearch": (3, 0)}  # (成功数, 失败数)
```

### 多索引写入

```python
# 初始化多个索引
provider = service.get_provider("opensearch")
provider.init_index("logs-auth")
provider.init_index("logs-payment")

# 写入到指定索引
await service.info_async("User login", service="auth", index="logs-auth")
await service.info_async("Payment success", service="payment", index="logs-payment")
```

### 多 Provider 写入

```python
from packages.log import LogService, OpenSearchProvider

service = LogService()
service.register_provider(OpenSearchProvider())
service.init()

# 写入到所有 Provider
await service.info_async("Log to all providers")

# 指定特定 Provider
await service.error_async("Error", service="api", providers=["opensearch"])
```

## API 参考

### LogService 方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `register_provider(provider)` | 注册 Provider | self |
| `unregister_provider(name)` | 注销 Provider | bool |
| `init(force, providers)` | 初始化 Provider | Dict[str, bool] |
| `is_ready(providers)` | 检查就绪状态 | Dict[str, bool] |
| `info(message, ...)` | 写入普通日志（同步） | Dict[str, str] |
| `info_async(message, ...)` | 写入普通日志（异步） | Dict[str, str] |
| `warn(message, ...)` | 写入警告日志（同步） | Dict[str, str] |
| `warn_async(message, ...)` | 写入警告日志（异步） | Dict[str, str] |
| `error(message, ...)` | 写入错误日志（同步） | Dict[str, str] |
| `error_async(message, ...)` | 写入错误日志（异步） | Dict[str, str] |
| `bulk_log(entries, ...)` | 批量写入（同步） | Dict[str, Tuple] |
| `bulk_log_async(entries, ...)` | 批量写入（异步） | Dict[str, Tuple] |
| `close()` | 关闭所有 Provider | None |

### 日志参数 (kwargs)

| 参数 | 类型 | 说明 |
|------|------|------|
| `user` | str | 用户名 |
| `user_id` | str | 用户 ID |
| `status_code` | int | HTTP 状态码 |
| `ip` | str | IP 地址 |
| `metadata` | dict | 扩展元数据 |
| `index` | str | 目标索引 |
| `providers` | list | 指定 Provider 列表 |

### 数据模型

**LogLevel** - 日志级别枚举

| 值 | 说明 |
|------|------|
| `LogLevel.LOG` | 普通日志 |
| `LogLevel.WARN` | 警告日志 |
| `LogLevel.ERROR` | 错误日志 |

**LogEntry** - 日志条目

```python
@dataclass
class LogEntry:
    message: str                    # 日志消息（必填）
    level: LogLevel = LogLevel.LOG  # 日志级别
    service: str = "default"        # 服务类别
    user: str = None                # 用户名
    user_id: str = None             # 用户 ID
    status_code: int = None         # HTTP 状态码
    ip: str = None                  # IP 地址
    metadata: dict = None           # 扩展元数据
    timestamp: datetime = None      # 时间戳（自动生成）
    index: str = None               # 目标索引
```

## 配置说明

### LogService 全局配置

```python
from packages.log import LogService, LogServiceConfig

config = LogServiceConfig(
    default_providers=["opensearch"],
    fail_silently=True,
)

service = LogService(config)
```

### OpenSearch 配置

**代码配置：**

```python
from packages.log import OpenSearchConfig

config = OpenSearchConfig(
    host="https://your-host/opensearch",
    username="admin",
    password="password",
    index_name="logs-backend",
    verify_certs=True,
    bulk_size=500,
)
```

**环境变量配置：**

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `OPENSEARCH_HOST` | 服务地址 | - |
| `OPENSEARCH_USERNAME` | 用户名 | admin |
| `OPENSEARCH_PASSWORD` | 密码 | - |
| `OPENSEARCH_INDEX_NAME` | 默认索引名 | logs-test |
| `OPENSEARCH_USE_SSL` | 启用 SSL | true |
| `OPENSEARCH_VERIFY_CERTS` | 验证证书 | true |

## 线程安全

LogService 是线程安全的：
- 单例创建使用类级别锁保护
- 写入操作使用实例级别锁保护
- 异步方法在线程池中执行

```python
# 多线程环境安全使用
from concurrent.futures import ThreadPoolExecutor

def log_in_thread(msg):
    service.info(msg, service="api")

with ThreadPoolExecutor(max_workers=10) as executor:
    for i in range(100):
        executor.submit(log_in_thread, f"Message {i}")
```

## 目录结构

```
log/
├── __init__.py              # 包入口
├── configs/
│   └── config.py            # LogService 配置
├── models/
│   └── models.py            # 数据模型
├── providers/
│   ├── base.py              # Provider 基类
│   └── opensearch/          # OpenSearch Provider
├── services/
│   └── service.py           # LogService 入口
├── example.py               # 使用示例
└── README.md
```
