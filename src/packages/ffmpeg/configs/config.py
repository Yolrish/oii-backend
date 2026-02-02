"""
FFmpeg 配置
"""
import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional
import shutil


# 环境变量名称
ENV_FFMPEG_PATH = "FFMPEG_PATH"
ENV_FFPROBE_PATH = "FFPROBE_PATH"
ENV_FFMPEG_TEMP_DIR = "FFMPEG_TEMP_DIR"


def _get_default_ffmpeg_path() -> str:
    """
    获取默认 ffmpeg 路径
    优先级：环境变量 > 默认值 "ffmpeg"
    """
    return os.environ.get(ENV_FFMPEG_PATH, "ffmpeg")


def _get_default_ffprobe_path() -> str:
    """
    获取默认 ffprobe 路径
    优先级：环境变量 > 默认值 "ffprobe"
    """
    return os.environ.get(ENV_FFPROBE_PATH, "ffprobe")


def _get_default_temp_dir() -> Optional[str]:
    """
    获取默认临时目录
    优先级：环境变量 > None（使用系统默认）
    """
    return os.environ.get(ENV_FFMPEG_TEMP_DIR)


@dataclass
class FFmpegConfig:
    """FFmpeg 配置类"""
    
    # FFmpeg 可执行文件路径
    # 优先级：显式指定 > 环境变量 > PATH 查找 > 默认值
    ffmpeg_path: str = field(default_factory=_get_default_ffmpeg_path)
    ffprobe_path: str = field(default_factory=_get_default_ffprobe_path)
    
    # 超时设置（秒）
    timeout: int = 3600  # 默认1小时
    
    # 默认编码参数
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5000k"
    audio_bitrate: str = "192k"
    
    # 临时文件目录
    # 优先级：显式指定 > 环境变量 FFMPEG_TEMP_DIR > 系统默认
    temp_dir: Optional[str] = field(default_factory=_get_default_temp_dir)
    
    # 日志级别: quiet, panic, fatal, error, warning, info, verbose, debug
    log_level: str = "error"
    
    def __post_init__(self):
        """初始化后验证"""
        self._resolve_ffmpeg_paths()
        self._validate_temp_dir()
    
    def _resolve_ffmpeg_paths(self):
        """解析 ffmpeg/ffprobe 路径"""
        # 如果是默认值（非绝对路径），尝试从 PATH 查找完整路径
        if self.ffmpeg_path and not os.path.isabs(self.ffmpeg_path):
            found = shutil.which(self.ffmpeg_path)
            if found:
                self.ffmpeg_path = found
        
        if self.ffprobe_path and not os.path.isabs(self.ffprobe_path):
            found = shutil.which(self.ffprobe_path)
            if found:
                self.ffprobe_path = found
    
    def _validate_temp_dir(self):
        """验证并创建临时目录"""
        if self.temp_dir:
            os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_temp_dir(self) -> str:
        """
        获取临时目录路径
        如果未指定则返回系统默认临时目录
        """
        return self.temp_dir or tempfile.gettempdir()


# 默认配置
default_config = FFmpegConfig()
