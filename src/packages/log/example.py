"""
日志服务使用示例

演示 LogService 的多 Provider 架构
"""

from log import (
    LogService,
    LogEntry,
    LogLevel,
    OpenSearchProvider,
    OpenSearchConfig,
    create_default_log_service,
)


def example_basic():
    """基础用法：使用快捷函数"""
    print("=" * 50)
    print("示例 1: 基础用法")
    print("=" * 50)
    
    # 使用快捷函数创建服务（自动注册 OpenSearch）
    service = create_default_log_service()
    
    # 初始化
    results = service.init(force=True)
    print(f"初始化结果: {results}")
    
    # 写入日志
    doc_ids = service.info("Application started", service="auth")
    print(f"INFO 结果: {doc_ids}")
    
    doc_ids = service.warn("High memory usage", service="system")
    print(f"WARN 结果: {doc_ids}")
    
    doc_ids = service.error(
        message="Database connection failed",
        service="ai",
        user="john_doe",
        user_id="usr_123",
        status_code=500,
        ip="192.168.1.100",
        metadata={"request_id": "req_abc", "retry_count": 3}
    )
    print(f"ERROR 结果: {doc_ids}")


def example_manual_register():
    """手动注册 Provider"""
    print("\n" + "=" * 50)
    print("示例 2: 手动注册 Provider")
    print("=" * 50)
    
    # 重置单例
    LogService.reset_instance()
    
    # 手动创建服务
    service = LogService()
    
    # 自定义配置
    config = OpenSearchConfig(
        host="https://log.reelnova.ai/opensearch",
        verify_certs=True,
    )
    
    # 注册 Provider（支持链式调用）
    service.register_provider(OpenSearchProvider(config))
    
    print(f"已注册的 Providers: {service.list_providers()}")
    
    # 初始化并写入
    service.init()
    service.info("Manual registration test", service="test")
    
    print("写入成功")


def example_multi_provider():
    """多 Provider 演示（模拟）"""
    print("\n" + "=" * 50)
    print("示例 3: 多 Provider 架构演示")
    print("=" * 50)
    
    LogService.reset_instance()
    service = LogService()
    
    # 注册 OpenSearch
    service.register_provider(OpenSearchProvider())
    
    # 未来可以注册更多 Provider：
    # service.register_provider(ElasticsearchProvider())
    # service.register_provider(FileLogProvider())
    # service.register_provider(CloudWatchProvider())
    
    print(f"已注册: {service.list_providers()}")
    
    # 初始化所有 Provider
    init_results = service.init()
    print(f"初始化: {init_results}")
    
    # 写入到所有 Provider
    results = service.info("Multi-provider test", service="demo")
    print(f"写入结果: {results}")
    
    # 指定特定 Provider（只写入到 opensearch）
    results = service.error(
        "Error log",
        service="demo",
        providers=["opensearch"]
    )
    print(f"指定 Provider 写入: {results}")


def example_bulk_write():
    """批量写入示例"""
    print("\n" + "=" * 50)
    print("示例 4: 批量写入")
    print("=" * 50)
    
    service = LogService.get_instance()
    
    # 创建多条日志
    entries = [
        LogEntry(message=f"Batch log {i}", level=LogLevel.LOG, service="batch")
        for i in range(5)
    ]
    
    # 批量写入
    results = service.bulk_log(entries)
    print(f"批量写入结果: {results}")


def example_multi_index():
    """多索引示例"""
    print("\n" + "=" * 50)
    print("示例 5: 多索引写入")
    print("=" * 50)
    
    LogService.reset_instance()
    service = create_default_log_service()
    
    # 获取 OpenSearch Provider 初始化多个索引
    provider = service.get_provider("opensearch")
    if provider:
        provider.init_index("logs-auth")      # 认证日志索引
        provider.init_index("logs-payment")   # 支付日志索引
        provider.init_index("logs-system")    # 系统日志索引
    
    # 写入到不同的索引
    service.info("User login", service="auth", index="logs-auth")
    print("写入 logs-auth 索引")
    
    service.info("Payment success", service="payment", index="logs-payment")
    print("写入 logs-payment 索引")
    
    service.warn("High CPU usage", service="system", index="logs-system")
    print("写入 logs-system 索引")
    
    # 批量写入到不同索引
    entries = [
        LogEntry(message="Auth log 1", service="auth", index="logs-auth"),
        LogEntry(message="Auth log 2", service="auth", index="logs-auth"),
        LogEntry(message="Payment log 1", service="payment", index="logs-payment"),
    ]
    results = service.bulk_log(entries)
    print(f"批量写入多索引结果: {results}")


if __name__ == "__main__":
    example_basic()
    # example_manual_register()
    # example_multi_provider()
    # example_bulk_write()
    # example_multi_index()
    
    print("\n✅ 所有示例执行完成")
