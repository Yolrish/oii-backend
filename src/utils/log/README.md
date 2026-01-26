# Log 日志服务

支持多 Provider 的统一日志写入服务，可灵活扩展不同的日志后端。

## 特性

- 🔌 **多 Provider 架构** - 支持同时写入多个日志后端
- 🎯 **单例模式** - 全局统一的日志服务入口
- 📦 **批量写入** - 支持单条和批量日志写入
- 🔧 **灵活配置** - 支持代码配置和环境变量
- 📊 **多索引** - 支持按业务分类存储到不同索引

## 快速开始

### 最简方式

```python
from log import create_default_log_service

# 创建服务（自动注册 OpenSearch Provider）
service = create_default_log_service()
service.init()

# 写入日志
service.info("User logged in", service="auth")
service.warn("High memory usage", service="system")
service.error("Connection failed", service="api", status_code=500)
```

### 手动配置

```python
from log import LogService, OpenSearchProvider, OpenSearchConfig

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
service.info("Hello", service="api")
```

## 日志写入

### 基础写入

```python
# 不同级别
service.info("普通日志", service="api")
service.warn("警告日志", service="api")
service.error("错误日志", service="api")

# 带用户信息
service.info("User action", service="api", user="john", user_id="12345")

# 带 HTTP 信息
service.error("Request failed", service="api", status_code=500, ip="192.168.1.1")

# 带扩展数据
service.info("Order created", service="order", metadata={"order_id": "ORD001", "amount": 99.9})
```

### 批量写入

```python
from log import LogEntry, LogLevel

entries = [
    LogEntry(message="Log 1", service="api"),
    LogEntry(message="Log 2", service="api", level=LogLevel.WARN),
    LogEntry(message="Log 3", service="api", user="john"),
]

results = service.bulk_log(entries)
# 返回: {"opensearch": (3, 0)}  # (成功数, 失败数)
```

### 多索引写入

按业务分类存储日志到不同索引：

```python
# 初始化多个索引
provider = service.get_provider("opensearch")
provider.init_index("logs-auth")      # 认证日志
provider.init_index("logs-payment")   # 支付日志
provider.init_index("logs-system")    # 系统日志

# 写入到指定索引
service.info("User login", service="auth", index="logs-auth")
service.info("Payment success", service="payment", index="logs-payment")
service.warn("High CPU", service="system", index="logs-system")

# 不指定则使用默认索引
service.info("Default index log")
```

### 多 Provider 写入

```python
from log import LogService, OpenSearchProvider

service = LogService()

# 注册多个 Provider
service.register_provider(OpenSearchProvider())
# service.register_provider(ElasticsearchProvider())  # 扩展
# service.register_provider(FileLogProvider())        # 扩展

service.init()

# 写入到所有 Provider
service.info("Log to all providers")

# 指定特定 Provider
service.error("Error", service="api", providers=["opensearch"])
```

## API 参考

### LogService 方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `register_provider(provider)` | 注册 Provider | self（支持链式调用） |
| `unregister_provider(name)` | 注销 Provider | bool |
| `get_provider(name)` | 获取指定 Provider | BaseLogProvider |
| `list_providers()` | 列出已注册的 Provider | List[str] |
| `init(force, providers)` | 初始化 Provider | Dict[str, bool] |
| `is_ready(providers)` | 检查 Provider 就绪状态 | Dict[str, bool] |
| `info(message, service, **kwargs)` | 写入普通日志 | Dict[str, str] |
| `warn(message, service, **kwargs)` | 写入警告日志 | Dict[str, str] |
| `error(message, service, **kwargs)` | 写入错误日志 | Dict[str, str] |
| `bulk_log(entries, providers)` | 批量写入 | Dict[str, Tuple] |
| `close()` | 关闭所有 Provider | None |

### 日志参数 (kwargs)

| 参数 | 类型 | 说明 |
|------|------|------|
| `user` | str | 用户名 |
| `user_id` | str | 用户 ID |
| `status_code` | int | HTTP 状态码 |
| `ip` | str | IP 地址 |
| `metadata` | dict | 扩展元数据（任意键值对） |
| `index` | str | 目标索引（不指定则使用默认索引） |
| `providers` | list | 指定写入的 Provider 列表 |

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
from log import LogService, LogServiceConfig

config = LogServiceConfig(
    default_providers=["opensearch"],  # 默认使用的 Provider 列表
    fail_silently=True,                # 写入失败时静默（不影响主业务）
)

service = LogService(config)
```

### OpenSearch 配置

**代码配置：**

```python
from log import OpenSearchConfig

config = OpenSearchConfig(
    host="https://your-host/opensearch",
    username="admin",
    password="password",
    index_name="logs-backend",
    verify_certs=True,
    bulk_size=500,              # 批量写入大小
    number_of_shards=1,         # 分片数
    number_of_replicas=0,       # 副本数
)
```

**环境变量配置：**

```python
config = OpenSearchConfig.from_env()
```

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `OPENSEARCH_HOST` | 服务地址 | - |
| `OPENSEARCH_USERNAME` | 用户名 | admin |
| `OPENSEARCH_PASSWORD` | 密码 | - |
| `OPENSEARCH_INDEX_NAME` | 默认索引名 | logs-test |
| `OPENSEARCH_USE_SSL` | 启用 SSL | true |
| `OPENSEARCH_VERIFY_CERTS` | 验证证书 | true |

## 扩展 Provider

在 `providers/` 目录下创建新模块，实现 `BaseLogProvider` 接口：

```python
from log.providers.base import BaseLogProvider
from log.models.models import LogEntry
from typing import List, Tuple, Optional

class MyProvider(BaseLogProvider):
    name = "my_provider"  # Provider 唯一标识
    
    def init(self, force: bool = False) -> bool:
        """初始化（如创建连接、索引等）"""
        return True
    
    def is_ready(self) -> bool:
        """检查是否就绪"""
        return True
    
    def write(self, entry: LogEntry) -> Optional[str]:
        """写入单条日志，返回文档 ID"""
        return "doc_id"
    
    def bulk_write(self, entries: List[LogEntry]) -> Tuple[int, int]:
        """批量写入，返回 (成功数, 失败数)"""
        return len(entries), 0
    
    def close(self) -> None:
        """关闭连接，释放资源"""
        pass

# 注册使用
service.register_provider(MyProvider())
```

## 目录结构

```
log/
├── __init__.py              # 包入口，导出公共 API
├── configs/
│   └── config.py            # LogService 全局配置
├── models/
│   └── models.py            # 数据模型（LogLevel, LogEntry）
├── providers/
│   ├── base.py              # Provider 抽象基类
│   └── opensearch/          # OpenSearch Provider
│       ├── config.py        # 连接和索引配置
│       ├── client.py        # OpenSearch 客户端封装
│       └── provider.py      # Provider 实现
├── services/
│   └── service.py           # LogService 统一入口
├── example.py               # 使用示例
└── README.md
```
