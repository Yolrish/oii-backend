"""
Packages 模块包

包含独立的功能模块：
- ffmpeg: 视频处理工具（视频信息、拼接、混音等）
- log: 日志服务（支持多 Provider 的日志写入）

使用示例：
    # FFmpeg 模块
    from packages.ffmpeg import create_ffmpeg_service
    service = create_ffmpeg_service()
    info = service.get_video_info("video.mp4")
    
    # Log 模块
    from packages.log import LogService, create_default_log_service
    service = create_default_log_service()
    service.init()
    service.info("Hello")
"""

# FFmpeg 模块
from .ffmpeg import (
    # 配置
    FFmpegConfig,
    default_config,
    # 模型
    ConcatMode,
    VideoInfo,
    VideoCompareResult,
    ConcatResult,
    MixAudioResult,
    # 客户端
    FFmpegError,
    FFmpegClient,
    FFmpegClientConfig,
    # 服务
    FFmpegService,
    get_default_service as get_ffmpeg_service,
    create_ffmpeg_service,
)

# Log 模块
from .log import (
    # 配置
    LogServiceConfig,
    LogLevel,
    LogEntry,
    # 核心
    BaseLogProvider,
    LogService,
    get_log_service,
    create_default_log_service,
    # Providers
    OpenSearchProvider,
    OpenSearchConfig,
)

__all__ = [
    # ===== FFmpeg =====
    # 配置
    "FFmpegConfig",
    "default_config",
    # 模型
    "ConcatMode",
    "VideoInfo",
    "VideoCompareResult",
    "ConcatResult",
    "MixAudioResult",
    # 客户端
    "FFmpegError",
    "FFmpegClient",
    "FFmpegClientConfig",
    # 服务
    "FFmpegService",
    "get_ffmpeg_service",
    "create_ffmpeg_service",
    # ===== Log =====
    # 配置
    "LogServiceConfig",
    "LogLevel",
    "LogEntry",
    # 核心
    "BaseLogProvider",
    "LogService",
    "get_log_service",
    "create_default_log_service",
    # Providers
    "OpenSearchProvider",
    "OpenSearchConfig",
]

__version__ = "1.0.0"
