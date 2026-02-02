"""
FFmpeg Services 模块
"""
from .service import (
    FFmpegService,
    get_default_service,
    create_ffmpeg_service,
)

__all__ = [
    "FFmpegService",
    "get_default_service",
    "create_ffmpeg_service",
]

