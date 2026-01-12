"""
FFmpeg 数据模型
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ConcatMode(str, Enum):
    """视频拼接模式"""
    COPY = "copy"          # 不重新编码，使用 concat demuxer
    REENCODE = "reencode"  # 重新编码，使用 filter_complex


@dataclass
class VideoInfo:
    """视频信息"""
    # 基本信息
    path: str
    duration: float = 0.0  # 时长（秒）
    size: int = 0          # 文件大小（字节）
    bitrate: int = 0       # 总比特率
    
    # 视频流信息
    video_codec: Optional[str] = None
    video_bitrate: Optional[int] = None
    width: int = 0
    height: int = 0
    fps: float = 0.0
    pixel_format: Optional[str] = None
    
    # 音频流信息
    audio_codec: Optional[str] = None
    audio_bitrate: Optional[int] = None
    sample_rate: int = 0
    channels: int = 0
    
    # 容器格式
    format_name: Optional[str] = None
    
    @property
    def resolution(self) -> str:
        """分辨率字符串"""
        return f"{self.width}x{self.height}"
    
    @property
    def has_video(self) -> bool:
        """是否有视频流"""
        return self.video_codec is not None
    
    @property
    def has_audio(self) -> bool:
        """是否有音频流"""
        return self.audio_codec is not None


@dataclass
class VideoCompareResult:
    """视频比较结果"""
    is_compatible: bool = False  # 是否兼容（可以不重新编码拼接）
    
    # 各项参数是否匹配
    codec_match: bool = False
    resolution_match: bool = False
    fps_match: bool = False
    audio_match: bool = False
    
    # 不匹配的详细信息
    differences: List[str] = field(default_factory=list)
    
    @property
    def can_concat_copy(self) -> bool:
        """是否可以使用 copy 模式拼接"""
        return self.is_compatible


@dataclass
class ConcatResult:
    """视频拼接结果"""
    success: bool = False
    output_path: Optional[str] = None
    mode: ConcatMode = ConcatMode.COPY
    
    # 输出视频信息
    duration: float = 0.0
    size: int = 0
    
    # 错误信息
    error_message: Optional[str] = None
    
    # 执行时间（秒）
    execution_time: float = 0.0


@dataclass
class MixAudioResult:
    """视频混音结果"""
    success: bool = False
    output_path: Optional[str] = None
    
    # 输出信息
    duration: float = 0.0
    size: int = 0
    
    # 音频是否循环
    audio_looped: bool = False
    
    # 错误信息
    error_message: Optional[str] = None
    
    # 执行时间（秒）
    execution_time: float = 0.0

