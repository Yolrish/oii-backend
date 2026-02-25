"""
Shell 模块数据模型
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class StreamType(str, Enum):
    """输出流类型"""
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass
class CommandResult:
    """命令执行结果"""
    
    # 执行状态
    success: bool = False           # return_code == 0
    return_code: int = -1           # 进程返回码
    
    # 输出内容
    stdout: str = ""                # 标准输出（完整）
    stderr: str = ""                # 标准错误（完整）
    
    # 命令信息
    command: str = ""               # 执行的命令
    cwd: Optional[str] = None       # 工作目录
    
    # 执行统计
    execution_time: float = 0.0     # 执行耗时（秒）
    timed_out: bool = False         # 是否超时
    
    @property
    def output(self) -> str:
        """获取合并的输出（stdout + stderr）"""
        if self.stderr:
            return f"{self.stdout}\n{self.stderr}".strip()
        return self.stdout
    
    @property
    def stdout_lines(self) -> List[str]:
        """获取 stdout 按行分割"""
        return self.stdout.splitlines() if self.stdout else []
    
    @property
    def stderr_lines(self) -> List[str]:
        """获取 stderr 按行分割"""
        return self.stderr.splitlines() if self.stderr else []
    
    def __bool__(self) -> bool:
        """支持 if result: 判断"""
        return self.success


@dataclass
class StreamLine:
    """流式输出的单行数据"""
    content: str                    # 行内容
    stream_type: StreamType         # 流类型
    line_number: int = 0            # 行号（从 1 开始）
