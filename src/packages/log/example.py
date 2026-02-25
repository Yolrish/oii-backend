"""
日志服务使用示例

运行方式：
    cd src
    python -m packages.log.example
"""
import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from packages.log import (
    LogService,
    LogEntry,
    LogLevel,
    OpenSearchProvider,
    OpenSearchConfig,
    create_default_log_service,
)


def example_basic():
    """基础用法：同步写入"""
    print("=" * 50)
    print("示例 1: 基础用法（同步）")
    print("=" * 50)
    
    # 使用快捷函数创建服务（自动注册 OpenSearch）
    service = create_default_log_service()
    
    # 初始化
    results = service.init(force=True)
    print(f"初始化结果: {results}")
    
    # 写入日志（同步）
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
    print()


async def example_async_basic():
    """异步写入示例"""
    print("=" * 50)
    print("示例 2: 异步写入（推荐在 Web 后端使用）")
    print("=" * 50)
    
    service = create_default_log_service()
    service.init()
    
    # 使用异步方法写入
    doc_ids = await service.info_async("Async log - INFO", service="api")
    print(f"INFO 结果: {doc_ids}")
    
    doc_ids = await service.warn_async("Async log - WARN", service="api")
    print(f"WARN 结果: {doc_ids}")
    
    doc_ids = await service.error_async(
        message="Async log - ERROR",
        service="api",
        status_code=500,
    )
    print(f"ERROR 结果: {doc_ids}")
    print()


def example_manual_register():
    """手动注册 Provider"""
    print("=" * 50)
    print("示例 3: 手动注册 Provider")
    print("=" * 50)
    
    # 重置单例
    LogService.reset_instance()
    
    # 手动创建服务
    service = LogService()
    
    # 自定义配置
    config = OpenSearchConfig(
        host="https://log.example.com/opensearch",
        verify_certs=True,
    )
    
    # 注册 Provider（支持链式调用）
    service.register_provider(OpenSearchProvider(config))
    
    print(f"已注册的 Providers: {service.list_providers()}")
    
    # 初始化并写入
    service.init()
    service.info("Manual registration test", service="test")
    
    print("写入成功")
    print()


def example_bulk_write():
    """批量写入示例（同步）"""
    print("=" * 50)
    print("示例 4: 批量写入（同步）")
    print("=" * 50)
    
    LogService.reset_instance()
    service = create_default_log_service()
    service.init()
    
    # 创建多条日志
    entries = [
        LogEntry(message=f"Batch log {i}", level=LogLevel.LOG, service="batch")
        for i in range(5)
    ]
    
    # 批量写入（同步）
    results = service.bulk_log(entries)
    print(f"批量写入结果: {results}")
    print()


async def example_bulk_write_async():
    """批量写入示例（异步）"""
    print("=" * 50)
    print("示例 5: 批量写入（异步）")
    print("=" * 50)
    
    service = LogService.get_instance()
    
    # 创建多条日志
    entries = [
        LogEntry(message=f"Async batch log {i}", level=LogLevel.LOG, service="batch")
        for i in range(5)
    ]
    
    # 批量写入（异步）
    results = await service.bulk_log_async(entries)
    print(f"异步批量写入结果: {results}")
    print()


async def example_concurrent_logging():
    """并发写入示例"""
    print("=" * 50)
    print("示例 6: 并发写入")
    print("=" * 50)
    
    service = LogService.get_instance()
    
    import time
    start = time.time()
    
    # 并发写入 10 条日志
    tasks = [
        service.info_async(f"Concurrent log {i}", service="concurrent")
        for i in range(10)
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"并发写入 10 条日志，耗时: {elapsed:.3f}秒")
    print(f"成功数: {sum(1 for r in results if r)}")
    print()


def example_multi_index():
    """多索引示例"""
    print("=" * 50)
    print("示例 7: 多索引写入")
    print("=" * 50)
    
    LogService.reset_instance()
    service = create_default_log_service()
    
    # 获取 OpenSearch Provider 初始化多个索引
    provider = service.get_provider("opensearch")
    if provider:
        provider.init_index("logs-auth")
        provider.init_index("logs-payment")
        provider.init_index("logs-system")
    
    # 写入到不同的索引
    service.info("User login", service="auth", index="logs-auth")
    print("写入 logs-auth 索引")
    
    service.info("Payment success", service="payment", index="logs-payment")
    print("写入 logs-payment 索引")
    
    service.warn("High CPU usage", service="system", index="logs-system")
    print("写入 logs-system 索引")
    print()


async def example_multi_index_async():
    """多索引异步写入示例"""
    print("=" * 50)
    print("示例 8: 多索引异步写入")
    print("=" * 50)
    
    service = LogService.get_instance()
    
    # 并发写入到不同索引
    tasks = [
        service.info_async("Async auth log", service="auth", index="logs-auth"),
        service.info_async("Async payment log", service="payment", index="logs-payment"),
        service.warn_async("Async system log", service="system", index="logs-system"),
    ]
    
    results = await asyncio.gather(*tasks)
    print(f"异步写入 {len(results)} 个索引完成")
    print()


def example_thread_safety():
    """线程安全示例"""
    print("=" * 50)
    print("示例 9: 线程安全（多线程写入）")
    print("=" * 50)
    
    from concurrent.futures import ThreadPoolExecutor
    import time
    
    LogService.reset_instance()
    service = create_default_log_service()
    service.init()
    
    def log_in_thread(msg: str):
        service.info(msg, service="thread")
        return True
    
    start = time.time()
    
    # 使用线程池并发写入
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(log_in_thread, f"Thread message {i}")
            for i in range(10)
        ]
        results = [f.result() for f in futures]
    
    elapsed = time.time() - start
    print(f"10 线程并发写入，耗时: {elapsed:.3f}秒")
    print(f"成功数: {sum(results)}")
    print()


async def example_fastapi_simulation():
    """模拟 FastAPI 使用场景"""
    print("=" * 50)
    print("示例 10: 模拟 FastAPI 使用")
    print("=" * 50)
    
    service = LogService.get_instance()
    
    # 模拟多个 API 请求同时写日志
    async def handle_request(request_id: int):
        await service.info_async(
            f"Request {request_id} received",
            service="api",
            metadata={"request_id": request_id}
        )
        # 模拟处理
        await asyncio.sleep(0.1)
        await service.info_async(
            f"Request {request_id} completed",
            service="api",
            metadata={"request_id": request_id}
        )
        return request_id
    
    import time
    start = time.time()
    
    # 模拟 5 个并发请求
    tasks = [handle_request(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"处理 5 个并发请求，耗时: {elapsed:.3f}秒")
    print(f"完成的请求: {results}")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 50)
    print("Log 模块使用示例")
    print("=" * 50 + "\n")
    
    # 同步示例
    example_basic()
    example_manual_register()
    example_bulk_write()
    example_multi_index()
    example_thread_safety()
    
    # 异步示例
    print("\n" + "=" * 50)
    print("异步示例")
    print("=" * 50 + "\n")
    
    asyncio.run(example_async_basic())
    asyncio.run(example_bulk_write_async())
    asyncio.run(example_concurrent_logging())
    asyncio.run(example_multi_index_async())
    asyncio.run(example_fastapi_simulation())
    
    print("=" * 50)
    print("所有示例执行完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
