# Log 日志服务

支持多 Provider 的日志写入服务，可灵活扩展不同的日志后端。

## 架构设计

```
log/
├── __init__.py                  # 包入口
├── configs/
│   └── config.py                # 全局配置（LogServiceConfig）
├── models/
│   └── models.py                # 数据模型（LogLevel, LogEntry）
├── providers/
│   ├── base.py                  # Provider 抽象基类
│   └── opensearch/              # OpenSearch Provider
│       ├── config.py
│       ├── client.py
│       └── provider.py
├── services/
│   └── service.py               # LogService（统一入口）
└── main.py                      # 使用示例
```

## 快速开始

```python
from log import create_default_log_service

# 创建服务（自动注册 OpenSearch）
service = create_default_log_service()
service.init()

# 写入日志
service.info("User logged in", service="auth")
service.warn("High memory", service="system")
service.error("Connection failed", service="api", status_code=500)
```

## 手动注册 Provider

```python
from log import LogService, OpenSearchProvider, OpenSearchConfig

service = LogService()

# 自定义配置
config = OpenSearchConfig(
    host="https://your-host/opensearch",
    username="admin",
    password="password",
)

# 注册 Provider
service.register_provider(OpenSearchProvider(config))
service.init()

# 写入
service.info("Hello")
```

## 多 Provider 使用

```python
from log import LogService, OpenSearchProvider

service = LogService()

# 注册多个 Provider
service.register_provider(OpenSearchProvider())
# service.register_provider(ElasticsearchProvider())  # 未来扩展
# service.register_provider(FileLogProvider())        # 未来扩展

# 初始化所有
service.init()

# 写入到所有 Provider
service.info("Log to all providers")

# 指定特定 Provider
service.error("Error", providers=["opensearch"])
```

## API

### LogService

| 方法 | 说明 |
|------|------|
| `register_provider(provider)` | 注册 Provider |
| `unregister_provider(name)` | 注销 Provider |
| `list_providers()` | 列出已注册的 Provider |
| `init(force, providers)` | 初始化 Provider |
| `info(message, service, **kwargs)` | 写入普通日志 |
| `warn(message, service, **kwargs)` | 写入警告日志 |
| `error(message, service, **kwargs)` | 写入错误日志 |
| `bulk_log(entries, providers)` | 批量写入 |

### 可选参数 (kwargs)

| 参数 | 类型 | 说明 |
|------|------|------|
| `user` | str | 用户名 |
| `user_id` | str | 用户 ID |
| `status_code` | int | HTTP 状态码 |
| `ip` | str | IP 地址 |
| `metadata` | dict | 扩展元数据 |
| `index` | str | 目标索引（用于 OpenSearch，不指定则使用默认索引） |
| `providers` | list | 指定使用的 Provider |

## 多索引使用

一个项目中可以使用多个索引，按业务分类存储日志：

```python
from log import create_default_log_service

service = create_default_log_service()

# 初始化多个索引
provider = service.get_provider("opensearch")
provider.init_index("logs-auth")      # 认证日志
provider.init_index("logs-payment")   # 支付日志
provider.init_index("logs-system")    # 系统日志

# 写入到不同索引
service.info("User login", service="auth", index="logs-auth")
service.info("Payment success", service="payment", index="logs-payment")
service.warn("High CPU", service="system", index="logs-system")

# 不指定 index 则使用默认索引（logs-backend）
service.info("Default index log")
```

## 扩展新的 Provider

在 `providers/` 下创建新目录，实现 `BaseLogProvider` 接口：

```python
from log.providers.base import BaseLogProvider
from log.models.models import LogEntry

class MyProvider(BaseLogProvider):
    name = "my_provider"
    
    def init(self, force=False) -> bool:
        return True
    
    def is_ready(self) -> bool:
        return True
    
    def write(self, entry: LogEntry) -> str:
        return "doc_id"
    
    def bulk_write(self, entries) -> tuple[int, int]:
        return len(entries), 0
    
    def close(self):
        pass

# 使用
service.register_provider(MyProvider())
```

## 配置

### 全局配置 (configs/config.py)

```python
from log import LogService, LogServiceConfig

config = LogServiceConfig(
    default_providers=["opensearch"],  # 默认使用的 Provider
    fail_silently=True,                # 写入失败时静默
)
service = LogService(config)
```

### OpenSearch 配置 (providers/opensearch/config.py)

```python
from log import OpenSearchConfig

config = OpenSearchConfig(
    host="https://your-host/opensearch",
    username="admin",
    password="password",
    index_name="logs-backend",
    verify_certs=True,
)
```

从环境变量加载：

```python
config = OpenSearchConfig.from_env()
```

支持的环境变量：
- `OPENSEARCH_HOST`
- `OPENSEARCH_USERNAME`
- `OPENSEARCH_PASSWORD`
- `OPENSEARCH_INDEX_NAME`
- `OPENSEARCH_VERIFY_CERTS`
