"""
FFmpeg Providers 模块
封装 FFmpeg 命令行调用
"""
from .exceptions import FFmpegError
from .client import FFmpegClient, FFmpegClientConfig

__all__ = [
    "FFmpegError",
    "FFmpegClient",
    "FFmpegClientConfig",
]
