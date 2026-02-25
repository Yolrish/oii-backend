"""
Shell 命令执行器

核心模块，提供同步/异步命令执行，支持：
- 并发调用（无状态设计）
- 实时流式输出（回调 / 生成器）
"""
import asyncio
import subprocess
import time
import threading
from typing import Optional, Dict, Callable, Generator, List

from ..configs.config import ShellConfig, default_config
from ..models.models import CommandResult, StreamType, StreamLine
from .exceptions import ShellTimeoutError, ShellExecutionError


# 输出回调函数类型
OutputCallback = Callable[[str], None]


class ShellExecutor:
    """
    Shell 命令执行器
    
    特性：
    - 无状态设计，天然支持并发调用
    - 支持实时流式输出（回调模式 / 生成器模式）
    - 同时提供同步和异步 API
    
    使用示例：
        executor = ShellExecutor()
        
        # 简单执行
        result = executor.run("git status")
        
        # 实时输出
        result = executor.run("pip install xxx", on_stdout=print)
        
        # 异步并发
        results = await asyncio.gather(
            executor.run_async("task1"),
            executor.run_async("task2"),
        )
    """
    
    def __init__(self, config: Optional[ShellConfig] = None):
        """
        初始化执行器
        
        Args:
            config: 可选配置，不传则使用默认配置
        """
        self.config = config or default_config
    
    # ==================== 同步执行 ====================
    
    def run(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        raise_on_error: Optional[bool] = None,
    ) -> CommandResult:
        """
        同步执行命令
        
        Args:
            command: 要执行的命令字符串
            cwd: 工作目录（覆盖配置）
            env: 环境变量（覆盖配置）
            timeout: 超时时间秒（覆盖配置，0 表示无限制）
            on_stdout: stdout 实时输出回调（每行触发一次）
            on_stderr: stderr 实时输出回调（每行触发一次）
            raise_on_error: 执行失败时是否抛出异常（覆盖配置）
        
        Returns:
            CommandResult 包含执行结果
        
        Raises:
            ShellTimeoutError: 命令执行超时（当 raise_on_error=True）
            ShellExecutionError: 命令执行失败（当 raise_on_error=True）
        """
        start_time = time.time()
        
        # 合并配置
        cwd = cwd or self.config.cwd
        env = env if env is not None else self.config.env
        timeout = timeout if timeout is not None else self.config.timeout
        raise_on_error = raise_on_error if raise_on_error is not None else self.config.raise_on_error
        
        # 准备结果对象
        result = CommandResult(command=command, cwd=cwd)
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        
        try:
            # 创建子进程
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                text=True,
                encoding=self.config.encoding,
                errors="replace",
                bufsize=1,  # 行缓冲
            )
            
            # 使用线程读取 stdout 和 stderr，实现实时输出
            def read_stream(stream, lines_list: List[str], callback: Optional[OutputCallback]):
                """读取流并触发回调"""
                try:
                    for line in iter(stream.readline, ""):
                        if line:
                            lines_list.append(line)
                            if callback:
                                callback(line)
                except Exception:
                    pass
                finally:
                    stream.close()
            
            # 启动读取线程
            stdout_thread = threading.Thread(
                target=read_stream,
                args=(process.stdout, stdout_lines, on_stdout),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream,
                args=(process.stderr, stderr_lines, on_stderr),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程完成（带超时）
            try:
                effective_timeout = timeout if timeout and timeout > 0 else None
                process.wait(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                result.timed_out = True
            
            # 等待读取线程完成
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            
            # 填充结果
            result.return_code = process.returncode
            result.success = (process.returncode == 0) and not result.timed_out
            result.stdout = "".join(stdout_lines)
            result.stderr = "".join(stderr_lines)
            
        except FileNotFoundError:
            result.return_code = 127
            result.stderr = f"命令未找到: {command.split()[0] if command else command}"
        except Exception as e:
            result.return_code = -1
            result.stderr = str(e)
        
        result.execution_time = time.time() - start_time
        
        # 根据配置决定是否抛出异常
        if raise_on_error:
            if result.timed_out:
                raise ShellTimeoutError(command, timeout or 0)
            if not result.success:
                raise ShellExecutionError(command, result.return_code, result.stderr)
        
        return result
    
    # ==================== 异步执行 ====================
    
    async def run_async(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
        raise_on_error: Optional[bool] = None,
    ) -> CommandResult:
        """
        异步执行命令（适合并发场景）
        
        Args:
            command: 要执行的命令字符串
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间秒（0 表示无限制）
            on_stdout: stdout 实时输出回调
            on_stderr: stderr 实时输出回调
            raise_on_error: 执行失败时是否抛出异常
        
        Returns:
            CommandResult 包含执行结果
        """
        start_time = time.time()
        
        # 合并配置
        cwd = cwd or self.config.cwd
        env = env if env is not None else self.config.env
        timeout = timeout if timeout is not None else self.config.timeout
        raise_on_error = raise_on_error if raise_on_error is not None else self.config.raise_on_error
        
        result = CommandResult(command=command, cwd=cwd)
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        
        try:
            # 创建异步子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
            
            async def read_stream_async(
                stream: asyncio.StreamReader,
                lines_list: List[str],
                callback: Optional[OutputCallback]
            ):
                """异步读取流"""
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode(self.config.encoding, errors="replace")
                    lines_list.append(line)
                    if callback:
                        callback(line)
            
            # 并发读取 stdout 和 stderr
            read_tasks = [
                read_stream_async(process.stdout, stdout_lines, on_stdout),
                read_stream_async(process.stderr, stderr_lines, on_stderr),
            ]
            
            try:
                effective_timeout = timeout if timeout and timeout > 0 else None
                await asyncio.wait_for(
                    asyncio.gather(*read_tasks),
                    timeout=effective_timeout
                )
                await process.wait()
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                result.timed_out = True
            
            result.return_code = process.returncode or 0
            result.success = (result.return_code == 0) and not result.timed_out
            result.stdout = "".join(stdout_lines)
            result.stderr = "".join(stderr_lines)
            
        except Exception as e:
            result.return_code = -1
            result.stderr = str(e)
        
        result.execution_time = time.time() - start_time
        
        if raise_on_error:
            if result.timed_out:
                raise ShellTimeoutError(command, timeout or 0)
            if not result.success:
                raise ShellExecutionError(command, result.return_code, result.stderr)
        
        return result
    
    # ==================== 生成器模式 ====================
    
    def stream(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Generator[StreamLine, None, CommandResult]:
        """
        生成器模式执行命令，逐行 yield 输出
        
        使用示例：
            gen = executor.stream("npm install")
            for line in gen:
                print(f"[{line.stream_type}] {line.content}")
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
            env: 环境变量
            timeout: 超时时间
        
        Yields:
            StreamLine 对象，包含每行内容和流类型
        
        Returns:
            CommandResult 最终执行结果
        """
        start_time = time.time()
        
        cwd = cwd or self.config.cwd
        env = env if env is not None else self.config.env
        timeout = timeout if timeout is not None else self.config.timeout
        
        result = CommandResult(command=command, cwd=cwd)
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        line_number = 0
        
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                text=True,
                encoding=self.config.encoding,
                errors="replace",
            )
            
            import selectors
            
            sel = selectors.DefaultSelector()
            sel.register(process.stdout, selectors.EVENT_READ, StreamType.STDOUT)
            sel.register(process.stderr, selectors.EVENT_READ, StreamType.STDERR)
            
            effective_timeout = timeout if timeout and timeout > 0 else None
            deadline = time.time() + effective_timeout if effective_timeout else None
            
            while sel.get_map():
                # 计算剩余超时时间
                if deadline:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        process.kill()
                        result.timed_out = True
                        break
                    select_timeout = min(remaining, 0.1)
                else:
                    select_timeout = 0.1
                
                events = sel.select(timeout=select_timeout)
                
                for key, _ in events:
                    stream_type: StreamType = key.data
                    line = key.fileobj.readline()
                    
                    if line:
                        line_number += 1
                        if stream_type == StreamType.STDOUT:
                            stdout_lines.append(line)
                        else:
                            stderr_lines.append(line)
                        
                        yield StreamLine(
                            content=line,
                            stream_type=stream_type,
                            line_number=line_number
                        )
                    else:
                        # 流结束
                        sel.unregister(key.fileobj)
                
                # 检查进程是否结束
                if process.poll() is not None:
                    # 读取剩余数据
                    for remaining_line in process.stdout:
                        line_number += 1
                        stdout_lines.append(remaining_line)
                        yield StreamLine(remaining_line, StreamType.STDOUT, line_number)
                    for remaining_line in process.stderr:
                        line_number += 1
                        stderr_lines.append(remaining_line)
                        yield StreamLine(remaining_line, StreamType.STDERR, line_number)
                    break
            
            sel.close()
            process.wait()
            
            result.return_code = process.returncode
            result.success = (process.returncode == 0) and not result.timed_out
            
        except Exception as e:
            result.return_code = -1
            result.stderr = str(e)
        
        result.stdout = "".join(stdout_lines)
        result.stderr = "".join(stderr_lines)
        result.execution_time = time.time() - start_time
        
        return result
    
    # ==================== 便捷方法 ====================
    
    def run_many(
        self,
        commands: List[str],
        *,
        stop_on_error: bool = True,
        cwd: Optional[str] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
    ) -> List[CommandResult]:
        """
        顺序执行多条命令
        
        Args:
            commands: 命令列表
            stop_on_error: 遇到错误时是否停止
            cwd: 工作目录
            on_stdout: stdout 回调
            on_stderr: stderr 回调
        
        Returns:
            CommandResult 列表
        """
        results: List[CommandResult] = []
        
        for cmd in commands:
            result = self.run(
                cmd,
                cwd=cwd,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
            )
            results.append(result)
            
            if stop_on_error and not result.success:
                break
        
        return results
    
    async def run_many_async(
        self,
        commands: List[str],
        *,
        concurrent: bool = True,
        stop_on_error: bool = True,
        cwd: Optional[str] = None,
        on_stdout: Optional[OutputCallback] = None,
        on_stderr: Optional[OutputCallback] = None,
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
        
        Returns:
            CommandResult 列表
        """
        if concurrent:
            # 并发执行
            tasks = [
                self.run_async(cmd, cwd=cwd, on_stdout=on_stdout, on_stderr=on_stderr)
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
                )
                results.append(result)
                if stop_on_error and not result.success:
                    break
            return results
