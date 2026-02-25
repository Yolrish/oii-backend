"""
Shell 模块异常定义
"""


class ShellError(Exception):
    """Shell 执行基础异常"""
    pass


class ShellTimeoutError(ShellError):
    """命令执行超时"""
    
    def __init__(self, command: str, timeout: int):
        self.command = command
        self.timeout = timeout
        super().__init__(f"命令执行超时 ({timeout}s): {command[:50]}...")


class ShellExecutionError(ShellError):
    """命令执行失败"""
    
    def __init__(self, command: str, return_code: int, stderr: str = ""):
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
        super().__init__(f"命令执行失败 (code={return_code}): {command[:50]}...")
