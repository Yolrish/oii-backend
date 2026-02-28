"""
Shell 服务层

提供高级封装和工厂函数，支持 Web 后端高并发场景
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Callable, Generator, List, AsyncGenerator

from ..configs.config import ShellConfig
from ..models.models import CommandResult, StreamLine
from ..providers.executor import ShellExecutor, OutputCallback


class ShellService:
    """
    Shell 服务
    
    对 ShellExecutor 的高级封装，支持 Web 后端高并发场景
    
    特性：
    - 并发控制：通过 Semaphore 限制同时执行的命令数
    - 线程池：同步方法可在线程池中执行，不阻塞事件循环
    - 异步优先：推荐使用 run_async() 方法
    
    使用示例：
        # FastAPI 中使用
        service = create_shell_service(max_concurrent=10)
        
        @app.get("/run")
        async def run_command(cmd: str):
            result = await service.run_async(cmd)
            return {"output": result.stdout}
    """
    
    def __init__(
        self,
        config: Optional[ShellConfig] = None,
        max_concurrent: int = 10,
        thread_pool_size: int = 4,
    ):
        """
        初始化服务
        
        Args:
            config: 可选配置
            max_concurrent: 最大并发执行数（防止资源耗尽）
            thread_pool_size: 线程池大小（用于同步方法的异步包装）
        """
        self.config = config or ShellConfig()
        self.executor = ShellExecutor(self.config)
        self.max_concurrent = max_concurrent
        
        # 并发控制信号量
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        # 线程池（用于在异步环境中执行同步方法）
        self._thread_pool = ThreadPoolExecutor(
            max_workers=thread_pool_size,
            thread_name_prefix="shell_"
        )
    
    @property
    def semaphore(self) -> asyncio.Semaphore:
        """获取信号量（懒加载，确保在正确的事件循环中创建）"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore
    
    # ==================== 同步方法 ====================
    
    def run(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        stdin_input: Optional[str] = None,
    ) -> CommandResult:
        """
        执行命令（同步）
        
        ⚠️ 警告：在 FastAPI 等异步框架中，请使用 run_async() 或 run_in_thread()
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间
            on_stdout: stdout 回调
            on_stderr: stderr 回调
            stdin_input: 可选，预写入子进程 stdin 的字符串（用于可预知选项的交互命令，如 npx）
        
        Returns:
            CommandResult
        """
        return self.executor.run(
            command,
            cwd=cwd,
            env=env,
            timeout=timeout,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
            stdin_input=stdin_input,
        )
    
    def stream(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        stdin_input: Optional[str] = None,
    ) -> Generator[StreamLine, None, CommandResult]:
        """
        生成器模式执行命令（同步）
        """
        return self.executor.stream(
            command,
            cwd=cwd,
            env=env,
            timeout=timeout,
            stdin_input=stdin_input,
        )
    
    def run_many(
        self,
        commands: List[str],
        *,
        stop_on_error: bool = True,
        cwd: Optional[str] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        stdin_input: Optional[str] = None,
    ) -> List[CommandResult]:
        """
        顺序执行多条命令（同步）
        """
        return self.executor.run_many(
            commands,
            stop_on_error=stop_on_error,
            cwd=cwd,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
            stdin_input=stdin_input,
        )
    
    # ==================== 异步方法（推荐在 Web 后端使用）====================
    
    async def run_async(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        use_semaphore: bool = True,
        stdin_input: Optional[str] = None,
    ) -> CommandResult:
        """
        执行命令（异步，推荐在 Web 后端使用）
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间
            on_stdout: stdout 回调
            on_stderr: stderr 回调
            use_semaphore: 是否使用信号量进行并发控制
            stdin_input: 可选，预写入子进程 stdin 的字符串（用于可预知选项的交互命令）
        
        Returns:
            CommandResult
        """
        if use_semaphore:
            async with self.semaphore:
                return await self.executor.run_async(
                    command,
                    cwd=cwd,
                    env=env,
                    timeout=timeout,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr,
                    stdin_input=stdin_input,
                )
        else:
            return await self.executor.run_async(
                command,
                cwd=cwd,
                env=env,
                timeout=timeout,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
                stdin_input=stdin_input,
            )
    
    async def run_in_thread(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        stdin_input: Optional[str] = None,
    ) -> CommandResult:
        """
        在线程池中执行同步命令（适用于需要同步特性但不想阻塞事件循环的场景）
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间
            on_stdout: stdout 回调
            on_stderr: stderr 回调
            stdin_input: 可选，预写入子进程 stdin 的字符串
        
        Returns:
            CommandResult
        """
        loop = asyncio.get_event_loop()
        
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.executor.run(
                    command,
                    cwd=cwd,
                    env=env,
                    timeout=timeout,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr,
                    stdin_input=stdin_input,
                )
            )
    
    async def stream_async(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        stdin_input: Optional[str] = None,
    ) -> AsyncGenerator[StreamLine, None]:
        """
        异步流式执行命令
        
        使用示例：
            async for line in service.stream_async("npm install"):
                print(line.content)
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间
            stdin_input: 可选，预写入子进程 stdin 的字符串
        
        Yields:
            StreamLine
        """
        import time
        from ..models.models import StreamType
        
        start_time = time.time()
        
        cwd = cwd or self.config.cwd
        env = env if env is not None else self.config.env
        timeout = timeout if timeout is not None else self.config.timeout
        
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        line_number = 0
        
        async with self.semaphore:
            stdin_arg = asyncio.subprocess.PIPE if stdin_input is not None else None
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=stdin_arg,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
            if stdin_input is not None and process.stdin is not None:
                try:
                    process.stdin.write(
                        stdin_input.encode(self.config.encoding, errors="replace")
                    )
                    await process.stdin.drain()
                finally:
                    process.stdin.close()
            
            async def read_stream(
                stream: asyncio.StreamReader,
                stream_type: StreamType,
                lines_list: List[str],
            ) -> AsyncGenerator[StreamLine, None]:
                nonlocal line_number
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode(self.config.encoding, errors="replace")
                    lines_list.append(line)
                    line_number += 1
                    yield StreamLine(
                        content=line,
                        stream_type=stream_type,
                        line_number=line_number,
                    )
            
            # 交替读取 stdout 和 stderr
            stdout_gen = read_stream(process.stdout, StreamType.STDOUT, stdout_lines)
            stderr_gen = read_stream(process.stderr, StreamType.STDERR, stderr_lines)
            
            # 使用 asyncio.Queue 合并两个流
            queue: asyncio.Queue[Optional[StreamLine]] = asyncio.Queue()
            
            async def feed_queue(gen: AsyncGenerator[StreamLine, None]):
                async for item in gen:
                    await queue.put(item)
            
            async def mark_done():
                await queue.put(None)
            
            # 启动读取任务
            tasks = [
                asyncio.create_task(feed_queue(stdout_gen)),
                asyncio.create_task(feed_queue(stderr_gen)),
            ]
            
            # 当所有任务完成时标记结束
            async def wait_and_mark():
                await asyncio.gather(*tasks)
                await mark_done()
            
            asyncio.create_task(wait_and_mark())
            
            # 从队列中读取并 yield
            done_count = 0
            while True:
                try:
                    effective_timeout = timeout if timeout and timeout > 0 else None
                    item = await asyncio.wait_for(queue.get(), timeout=effective_timeout)
                    if item is None:
                        break
                    yield item
                except asyncio.TimeoutError:
                    process.kill()
                    break
            
            await process.wait()
    
    async def run_many_async(
        self,
        commands: List[str],
        *,
        concurrent: bool = True,
        stop_on_error: bool = True,
        cwd: Optional[str] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        stdin_input: Optional[str] = None,
    ) -> List[CommandResult]:
        """
        异步执行多条命令
        
        Args:
            commands: 命令列表
            concurrent: 是否并发执行（True 并发，False 顺序）
            stop_on_error: 顺序执行时遇到错误是否停止
            cwd: 工作目录
            on_stdout: stdout 回调
            on_stderr: stderr 回调
            stdin_input: 可选，预写入每条命令 stdin 的字符串
        
        Returns:
            CommandResult 列表
        """
        if concurrent:
            # 并发执行（信号量会自动控制并发数）
            tasks = [
                self.run_async(
                    cmd,
                    cwd=cwd,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr,
                    use_semaphore=True,
                    stdin_input=stdin_input,
                )
                for cmd in commands
            ]
            return await asyncio.gather(*tasks)
        else:
            # 顺序执行
            results: List[CommandResult] = []
            for cmd in commands:
                result = await self.run_async(
                    cmd,
                    cwd=cwd,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr,
                    use_semaphore=True,
                    stdin_input=stdin_input,
                )
                results.append(result)
                if stop_on_error and not result.success:
                    break
            return results
    
    # ==================== 资源管理 ====================
    
    def close(self):
        """关闭服务，释放资源"""
        self._thread_pool.shutdown(wait=False)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.close()


# ==================== 工厂函数 ====================

# 默认服务实例（懒加载）
_default_service: Optional[ShellService] = None


def get_default_service() -> ShellService:
    """
    获取默认服务实例（懒加载单例）
    
    适用于使用默认配置的场景
    """
    global _default_service
    if _default_service is None:
        _default_service = ShellService()
    return _default_service


def create_shell_service(
    config: Optional[ShellConfig] = None,
    max_concurrent: int = 10,
    thread_pool_size: int = 4,
) -> ShellService:
    """
    创建新的 Shell 服务实例
    
    Args:
        config: 可选的自定义配置
        max_concurrent: 最大并发执行数
        thread_pool_size: 线程池大小
    
    Returns:
        ShellService 实例
    """
    return ShellService(
        config=config,
        max_concurrent=max_concurrent,
        thread_pool_size=thread_pool_size,
    )


# ==================== 快捷函数 ====================

def run(
    command: str,
    *,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    on_stdout: Optional[OutputCallback] = None,
    on_stderr: Optional[OutputCallback] = None,
    stdin_input: Optional[str] = None,
) -> CommandResult:
    """
    快捷函数：执行命令（同步）
    
    ⚠️ 警告：在异步环境中请使用 run_async()
    """
    return get_default_service().run(
        command,
        cwd=cwd,
        timeout=timeout,
        on_stdout=on_stdout,
        on_stderr=on_stderr,
        stdin_input=stdin_input,
    )


async def run_async(
    command: str,
    *,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    on_stdout: Optional[OutputCallback] = None,
    on_stderr: Optional[OutputCallback] = None,
    stdin_input: Optional[str] = None,
) -> CommandResult:
    """
    快捷函数：执行命令（异步，推荐在 Web 后端使用）
    """
    return await get_default_service().run_async(
        command,
        cwd=cwd,
        timeout=timeout,
        on_stdout=on_stdout,
        on_stderr=on_stderr,
        stdin_input=stdin_input,
    )
