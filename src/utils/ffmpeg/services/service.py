"""
FFmpeg Service
提供视频处理功能
"""
from typing import List, Optional

from ..configs.config import FFmpegConfig
from ..models.models import (
    VideoInfo,
    VideoCompareResult,
    ConcatResult,
    ConcatMode,
    MixAudioResult,
)
from ..providers.client import FFmpegClient, FFmpegClientConfig


class FFmpegService:
    """
    FFmpeg 服务
    提供高级的视频处理功能
    """
    
    def __init__(self, config: Optional[FFmpegConfig] = None):
        self.config = config or FFmpegConfig()
        self.client: Optional[FFmpegClient] = None
    
    def init(self) -> bool:
        """
        初始化服务
        
        Returns:
            是否初始化成功
        """
        # 创建客户端配置
        client_config = FFmpegClientConfig(
            ffmpeg_path=self.config.ffmpeg_path,
            ffprobe_path=self.config.ffprobe_path,
            timeout=self.config.timeout,
            video_codec=self.config.video_codec,
            audio_codec=self.config.audio_codec,
            video_bitrate=self.config.video_bitrate,
            audio_bitrate=self.config.audio_bitrate,
            temp_dir=self.config.temp_dir,
            log_level=self.config.log_level,
        )
        self.client = FFmpegClient(client_config)
        
        return self.client.is_available()
    
    def _ensure_client(self):
        """确保 client 已初始化"""
        if not self.client:
            self.init()
    
    # ==================== 核心功能 ====================
    
    def get_video_info(self, video_path: str) -> VideoInfo:
        """
        获取视频信息
        """
        self._ensure_client()
        return self.client.get_video_info(video_path)
    
    def compare_videos(
        self, 
        video1_path: str, 
        video2_path: str
    ) -> VideoCompareResult:
        """
        比较两个视频是否兼容
        """
        self._ensure_client()
        return self.client.compare_videos(video1_path, video2_path)
    
    def concat_videos(
        self,
        video_paths: List[str],
        output_path: str,
        mode: Optional[ConcatMode] = None,
        auto_detect: bool = True,
        **kwargs
    ) -> ConcatResult:
        """
        拼接多个视频
        
        Args:
            video_paths: 视频文件路径列表
            output_path: 输出文件路径
            mode: 拼接模式（COPY 或 REENCODE）
            auto_detect: 是否自动检测模式
            **kwargs: 重新编码参数
        
        Returns:
            ConcatResult 对象
        """
        self._ensure_client()
        
        if len(video_paths) < 2:
            return ConcatResult(
                success=False,
                error_message="至少需要两个视频文件"
            )
        
        # 自动检测模式
        if mode is None and auto_detect:
            mode = self._detect_concat_mode(video_paths)
        elif mode is None:
            mode = ConcatMode.COPY
        
        if mode == ConcatMode.COPY:
            return self.client.concat_copy(video_paths, output_path)
        else:
            return self.client.concat_reencode(video_paths, output_path, **kwargs)
    
    def concat_videos_copy(
        self,
        video_paths: List[str],
        output_path: str
    ) -> ConcatResult:
        """
        不重新编码拼接视频
        """
        self._ensure_client()
        return self.client.concat_copy(video_paths, output_path)
    
    def concat_videos_reencode(
        self,
        video_paths: List[str],
        output_path: str,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        video_bitrate: Optional[str] = None,
        audio_bitrate: Optional[str] = None,
        resolution: Optional[str] = None,
        fps: Optional[float] = None
    ) -> ConcatResult:
        """
        重新编码拼接视频
        """
        self._ensure_client()
        return self.client.concat_reencode(
            video_paths=video_paths,
            output_path=output_path,
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate,
            resolution=resolution,
            fps=fps
        )
    
    # ==================== 视频混音 ====================
    
    def mix_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        loop_audio: bool = True,
        replace_original: bool = True,
        audio_volume: float = 1.0,
        original_volume: float = 0.0,
        audio_codec: Optional[str] = None,
        audio_bitrate: Optional[str] = None
    ) -> MixAudioResult:
        """
        将音频文件作为视频的背景音乐
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            loop_audio: 音频时长不足时是否循环（默认 True）
            replace_original: 是否替换原视频音频（默认 True）
            audio_volume: 背景音乐音量（0.0-1.0，默认 1.0）
            original_volume: 原视频音量（0.0-1.0，默认 0.0 即静音）
            audio_codec: 音频编码器
            audio_bitrate: 音频比特率
        
        Returns:
            MixAudioResult 对象
        """
        self._ensure_client()
        return self.client.mix_audio(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            loop_audio=loop_audio,
            replace_original=replace_original,
            audio_volume=audio_volume,
            original_volume=original_volume,
            audio_codec=audio_codec,
            audio_bitrate=audio_bitrate
        )
    
    # ==================== 工具方法 ====================
    
    def _detect_concat_mode(self, video_paths: List[str]) -> ConcatMode:
        """自动检测拼接模式"""
        if len(video_paths) < 2:
            return ConcatMode.COPY
        
        first_video = video_paths[0]
        
        for video_path in video_paths[1:]:
            result = self.client.compare_videos(first_video, video_path)
            if not result.is_compatible:
                return ConcatMode.REENCODE
        
        return ConcatMode.COPY
    
    def is_available(self) -> bool:
        """检查 FFmpeg 是否可用"""
        self._ensure_client()
        return self.client.is_available()
    
    def get_version(self) -> Optional[str]:
        """获取 FFmpeg 版本"""
        self._ensure_client()
        return self.client.get_version()
    
    def check_compatibility(self, video_paths: List[str]) -> dict:
        """
        检查多个视频的兼容性
        """
        self._ensure_client()
        
        if len(video_paths) < 2:
            return {
                "compatible": True,
                "recommended_mode": ConcatMode.COPY,
                "comparisons": [],
                "all_differences": []
            }
        
        comparisons = []
        all_differences = []
        all_compatible = True
        
        first_video = video_paths[0]
        
        for i, video_path in enumerate(video_paths[1:], start=1):
            result = self.client.compare_videos(first_video, video_path)
            comparisons.append({
                "video1": first_video,
                "video2": video_path,
                "compatible": result.is_compatible,
                "differences": result.differences
            })
            
            if not result.is_compatible:
                all_compatible = False
                all_differences.extend(result.differences)
        
        return {
            "compatible": all_compatible,
            "recommended_mode": ConcatMode.COPY if all_compatible else ConcatMode.REENCODE,
            "comparisons": comparisons,
            "all_differences": list(set(all_differences))
        }


# ==================== 工厂函数 ====================

# 默认服务实例（懒加载）
_default_service: Optional[FFmpegService] = None


def get_default_service() -> FFmpegService:
    """
    获取默认服务实例（懒加载）
    适用于使用默认配置的场景
    """
    global _default_service
    if _default_service is None:
        _default_service = FFmpegService()
        _default_service.init()
    return _default_service


def create_ffmpeg_service(config: Optional[FFmpegConfig] = None) -> FFmpegService:
    """
    创建新的 FFmpeg 服务实例
    
    Args:
        config: 可选的自定义配置
    
    Returns:
        已初始化的 FFmpegService 实例
    """
    service = FFmpegService(config)
    service.init()
    return service
