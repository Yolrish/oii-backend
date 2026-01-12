"""
FFmpeg 工具模块

封装 FFmpeg 命令行调用，提供视频处理功能：
- 获取视频信息
- 比较视频参数
- 视频拼接（不重编码/重编码）
- 视频混音（添加背景音乐）

使用示例：
    from utils.ffmpeg import create_ffmpeg_service
    
    # 创建服务（推荐）
    service = create_ffmpeg_service()
    
    # 获取视频信息
    info = service.get_video_info("video.mp4")
    
    # 拼接视频（自动检测模式）
    result = service.concat_videos(
        video_paths=["part1.mp4", "part2.mp4"],
        output_path="output.mp4"
    )
    
    # 添加背景音乐
    result = service.mix_audio(
        video_path="video.mp4",
        audio_path="bgm.mp3",
        output_path="output.mp4",
        loop_audio=True  # 音乐不够长时循环
    )

使用默认实例：
    from utils.ffmpeg import get_default_service
    
    service = get_default_service()  # 懒加载的默认实例

自定义配置：
    from utils.ffmpeg import FFmpegConfig, create_ffmpeg_service
    
    config = FFmpegConfig(
        video_codec="libx265",
        video_bitrate="8000k"
    )
    service = create_ffmpeg_service(config)
"""

# 配置
from .configs.config import FFmpegConfig, default_config

# 模型
from .models.models import (
    ConcatMode,
    VideoInfo,
    VideoCompareResult,
    ConcatResult,
    MixAudioResult,
)

# 客户端
from .providers.exceptions import FFmpegError
from .providers.client import FFmpegClient, FFmpegClientConfig

# 服务
from .services.service import (
    FFmpegService,
    get_default_service,
    create_ffmpeg_service,
)

__all__ = [
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
    "get_default_service",
    "create_ffmpeg_service",
]

__version__ = "1.0.0"
