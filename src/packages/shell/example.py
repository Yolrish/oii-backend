"""
Shell 模块使用示例

运行方式：
    cd src
    python -m packages.shell.example
"""
import asyncio
import sys
import os
import time

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from packages.shell import (
    ShellService,
    ShellConfig,
    create_shell_service,
    run,
    run_async,
    CommandResult,
)


def example_basic():
    """基础用法示例"""
    print("=" * 50)
    print("示例 1: 基础用法（同步）")
    print("=" * 50)
    
    service = create_shell_service()
    
    # 简单执行
    result = service.run("echo Hello World")
    print(f"命令: {result.command}")
    print(f"成功: {result.success}")
    print(f"输出: {result.stdout.strip()}")
    print(f"耗时: {result.execution_time:.3f}s")
    print()


async def example_async_basic():
    """异步基础用法"""
    print("=" * 50)
    print("示例 2: 异步执行（推荐在 Web 后端使用）")
    print("=" * 50)
    
    service = create_shell_service()
    
    # 异步执行
    result = await service.run_async("echo Async Hello")
    print(f"命令: {result.command}")
    print(f"成功: {result.success}")
    print(f"输出: {result.stdout.strip()}")
    print()


def example_realtime_output():
    """实时输出示例（同步）"""
    print("=" * 50)
    print("示例 3: 实时输出（回调模式）")
    print("=" * 50)
    
    service = create_shell_service()
    
    def on_output(line: str):
        print(f"[实时] {line}", end="")
    
    if sys.platform == "win32":
        cmd = "ping -n 3 127.0.0.1"
    else:
        cmd = "for i in 1 2 3; do echo Line $i; sleep 0.5; done"
    
    result = service.run(cmd, on_stdout=on_output, on_stderr=on_output)
    print(f"\n执行完成，耗时: {result.execution_time:.3f}s")
    print()


async def example_async_realtime():
    """异步实时输出示例"""
    print("=" * 50)
    print("示例 4: 异步实时输出")
    print("=" * 50)
    
    service = create_shell_service()
    
    def on_output(line: str):
        print(f"[异步实时] {line}", end="")
    
    if sys.platform == "win32":
        cmd = "ping -n 2 127.0.0.1"
    else:
        cmd = "for i in 1 2; do echo Line $i; sleep 0.3; done"
    
    result = await service.run_async(cmd, on_stdout=on_output)
    print(f"\n执行完成，耗时: {result.execution_time:.3f}s")
    print()


def example_stream():
    """生成器模式示例"""
    print("=" * 50)
    print("示例 5: 生成器模式（同步）")
    print("=" * 50)
    
    service = create_shell_service()
    
    if sys.platform == "win32":
        cmd = "dir"
    else:
        cmd = "ls -la"
    
    print(f"执行: {cmd}")
    for line in service.stream(cmd):
        print(f"[{line.stream_type.value:6}] {line.content}", end="")
    print()


async def example_stream_async():
    """异步生成器模式示例"""
    print("=" * 50)
    print("示例 6: 异步生成器模式")
    print("=" * 50)
    
    service = create_shell_service()
    
    if sys.platform == "win32":
        cmd = "echo Line1 && echo Line2 && echo Line3"
    else:
        cmd = "echo Line1; echo Line2; echo Line3"
    
    print(f"执行: {cmd}")
    async for line in service.stream_async(cmd):
        print(f"[异步流] {line.content}", end="")
    print()


def example_quick_function():
    """快捷函数示例"""
    print("=" * 50)
    print("示例 7: 快捷函数")
    print("=" * 50)
    
    # 同步快捷函数
    result = run("echo Quick function test")
    print(f"同步输出: {result.stdout.strip()}")
    print()


async def example_quick_function_async():
    """异步快捷函数示例"""
    print("=" * 50)
    print("示例 8: 异步快捷函数")
    print("=" * 50)
    
    # 异步快捷函数
    result = await run_async("echo Async quick function")
    print(f"异步输出: {result.stdout.strip()}")
    print()


def example_run_many():
    """批量执行示例（同步）"""
    print("=" * 50)
    print("示例 9: 批量执行（同步）")
    print("=" * 50)
    
    service = create_shell_service()
    
    commands = [
        "echo Step 1",
        "echo Step 2",
        "echo Step 3",
    ]
    
    results = service.run_many(commands)
    
    for i, result in enumerate(results, 1):
        print(f"命令 {i}: {result.stdout.strip()}")
    print()


async def example_concurrent():
    """并发执行示例"""
    print("=" * 50)
    print("示例 10: 并发执行")
    print("=" * 50)
    
    service = create_shell_service(max_concurrent=10)
    
    if sys.platform == "win32":
        commands = [
            "echo Task A && ping -n 2 127.0.0.1 > nul && echo Task A done",
            "echo Task B && ping -n 1 127.0.0.1 > nul && echo Task B done",
            "echo Task C done",
        ]
    else:
        commands = [
            "echo Task A && sleep 0.5 && echo Task A done",
            "echo Task B && sleep 0.3 && echo Task B done",
            "echo Task C done",
        ]
    
    print("并发执行 3 个任务...")
    start = time.time()
    
    results = await service.run_many_async(commands, concurrent=True)
    
    elapsed = time.time() - start
    print(f"全部完成，总耗时: {elapsed:.3f}s")
    
    for i, result in enumerate(results, 1):
        output = result.stdout.strip().replace('\n', ' | ')
        print(f"任务 {i}: {output}")
    print()


async def example_concurrent_with_limit():
    """并发控制示例"""
    print("=" * 50)
    print("示例 11: 并发控制（Semaphore）")
    print("=" * 50)
    
    # 创建服务，限制最大并发数为 2
    service = create_shell_service(max_concurrent=2)
    
    if sys.platform == "win32":
        commands = [f"echo Task {i} && ping -n 1 127.0.0.1 > nul" for i in range(5)]
    else:
        commands = [f"echo Task {i} && sleep 0.2" for i in range(5)]
    
    print(f"执行 {len(commands)} 个任务，max_concurrent=2")
    print("（即使同时发起，也只会同时执行 2 个）")
    
    start = time.time()
    results = await service.run_many_async(commands, concurrent=True)
    elapsed = time.time() - start
    
    print(f"全部完成，耗时: {elapsed:.3f}s")
    print(f"成功数: {sum(1 for r in results if r.success)}")
    print()


async def example_concurrent_with_output():
    """并发执行 + 实时输出示例"""
    print("=" * 50)
    print("示例 12: 并发执行 + 实时输出")
    print("=" * 50)
    
    service = create_shell_service()
    
    async def task_with_tag(tag: str, cmd: str):
        def on_output(line: str):
            print(f"[{tag}] {line}", end="")
        
        return await service.run_async(cmd, on_stdout=on_output)
    
    if sys.platform == "win32":
        tasks = [
            task_with_tag("A", "echo A-1 && ping -n 1 127.0.0.1 > nul && echo A-2"),
            task_with_tag("B", "echo B-1 && echo B-2"),
        ]
    else:
        tasks = [
            task_with_tag("A", "echo A-1 && sleep 0.3 && echo A-2"),
            task_with_tag("B", "echo B-1 && sleep 0.1 && echo B-2"),
        ]
    
    await asyncio.gather(*tasks)
    print()


def example_custom_config():
    """自定义配置示例"""
    print("=" * 50)
    print("示例 13: 自定义配置")
    print("=" * 50)
    
    config = ShellConfig(
        timeout=10,
        encoding="utf-8",
        raise_on_error=False,
    )
    
    service = create_shell_service(
        config=config,
        max_concurrent=5,
        thread_pool_size=2,
    )
    
    result = service.run("echo Custom config test")
    print(f"输出: {result.stdout.strip()}")
    print()


def example_timeout():
    """超时处理示例"""
    print("=" * 50)
    print("示例 14: 超时处理")
    print("=" * 50)
    
    service = create_shell_service()
    
    if sys.platform == "win32":
        cmd = "ping -n 10 127.0.0.1"
    else:
        cmd = "sleep 10"
    
    print(f"执行命令（设置 2 秒超时）: {cmd}")
    result = service.run(cmd, timeout=2)
    
    print(f"是否超时: {result.timed_out}")
    print(f"返回码: {result.return_code}")
    print()


async def example_resource_management():
    """资源管理示例"""
    print("=" * 50)
    print("示例 15: 资源管理（上下文管理器）")
    print("=" * 50)
    
    # 使用上下文管理器
    async with create_shell_service() as service:
        result = await service.run_async("echo Context manager test")
        print(f"输出: {result.stdout.strip()}")
    
    print("退出上下文时自动释放资源")
    print()


async def example_fastapi_simulation():
    """模拟 FastAPI 使用场景"""
    print("=" * 50)
    print("示例 16: 模拟 FastAPI 高并发场景")
    print("=" * 50)
    
    service = create_shell_service(max_concurrent=5)
    
    async def handle_request(request_id: int):
        """模拟 API 请求处理"""
        result = await service.run_async(f"echo Request {request_id} processed")
        return request_id, result.success
    
    print("模拟 10 个并发 API 请求...")
    start = time.time()
    
    tasks = [handle_request(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"处理 10 个请求，耗时: {elapsed:.3f}s")
    print(f"成功数: {sum(1 for _, success in results if success)}")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 50)
    print("Shell 模块使用示例")
    print("=" * 50 + "\n")
    
    # 同步示例
    example_basic()
    example_realtime_output()
    example_stream()
    example_quick_function()
    example_run_many()
    example_custom_config()
    example_timeout()
    
    # 异步示例
    print("\n" + "=" * 50)
    print("异步示例")
    print("=" * 50 + "\n")
    
    asyncio.run(example_async_basic())
    asyncio.run(example_async_realtime())
    asyncio.run(example_stream_async())
    asyncio.run(example_quick_function_async())
    asyncio.run(example_concurrent())
    asyncio.run(example_concurrent_with_limit())
    asyncio.run(example_concurrent_with_output())
    asyncio.run(example_resource_management())
    asyncio.run(example_fastapi_simulation())
    
    print("=" * 50)
    print("所有示例执行完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
