"""
Packages 模块包

包含独立的功能模块：
- ffmpeg: 视频处理工具（视频信息、拼接、混音等）
- log: 日志服务（支持多 Provider 的日志写入）
- shell: 命令行执行器（支持并发、实时输出）
- workflow: 动态工作流（Step 串行、Task 并行、生命周期回调）

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
    
    # Shell 模块
    from packages.shell import run, ShellExecutor
    result = run("git status")
    # 或使用执行器
    executor = ShellExecutor()
    result = executor.run("echo hello", on_stdout=print)
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

# Workflow 模块
from .workflow import (
    WorkflowConfig,
    default_config as workflow_default_config,
    StepCallbacks,
    TaskCallbacks,
    Task,
    Step,
    Workflow,
    StepResult,
    TaskResult,
    WorkflowResult,
    WorkflowService,
    create_workflow_service,
    get_default_service as get_workflow_service,
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
    # ===== Workflow =====
    "WorkflowConfig",
    "workflow_default_config",
    "StepCallbacks",
    "TaskCallbacks",
    "Task",
    "Step",
    "Workflow",
    "StepResult",
    "TaskResult",
    "WorkflowResult",
    "WorkflowService",
    "create_workflow_service",
    "get_workflow_service",
]

__version__ = "1.0.0"
