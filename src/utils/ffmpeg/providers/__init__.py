"""
FFmpeg Providers 模块
封装 FFmpeg 命令行调用
"""
from utils.ffmpeg.providers.exceptions import FFmpegError
from utils.ffmpeg.providers.client import FFmpegClient, FFmpegClientConfig

__all__ = [
    "FFmpegError",
    "FFmpegClient",
    "FFmpegClientConfig",
]
