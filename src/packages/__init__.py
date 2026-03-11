"""
Packages 基础能力模块

独立、可复用的基础功能模块（不含业务编排逻辑）：
- ffmpeg: 视频处理工具（视频信息、拼接、混音等）
- log: 日志服务（支持多 Provider 的日志写入）
- shell: 命令行执行器（支持并发、实时输出）
- tool_call: 工具注册与执行
- claude: Claude 对话 SDK 封装

业务编排模块（chat、workflow）已迁移到 features/ 下。
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

# Shell 模块
from .shell import (
    # 配置
    ShellConfig,
    # 模型
    CommandResult,
    StreamType,
    StreamLine,
    # 异常
    ShellError,
    ShellTimeoutError,
    ShellExecutionError,
    # 执行器
    ShellExecutor,
    # 服务
    ShellService,
    get_default_service as get_shell_service,
    create_shell_service,
    # 快捷函数
    run as shell_run,
    run_async as shell_run_async,
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
    # ===== Shell =====
    # 配置
    "ShellConfig",
    # 模型
    "CommandResult",
    "StreamType",
    "StreamLine",
    # 异常
    "ShellError",
    "ShellTimeoutError",
    "ShellExecutionError",
    # 执行器
    "ShellExecutor",
    # 服务
    "ShellService",
    "get_shell_service",
    "create_shell_service",
    # 快捷函数
    "shell_run",
    "shell_run_async",
]

__version__ = "1.0.0"
