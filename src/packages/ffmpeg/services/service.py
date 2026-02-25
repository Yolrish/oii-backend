"""
FFmpeg Service
提供视频处理功能，支持 Web 后端高并发场景
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
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
    
    提供高级的视频处理功能，支持高并发场景
    
    特性：
    - 异步方法：所有核心功能都有 async 版本
    - 并发控制：通过 Semaphore 限制同时处理的视频数
    - 线程池：CPU 密集型操作在线程池中执行
    
    使用示例：
        # FastAPI 中使用
        service = create_ffmpeg_service(max_concurrent=3)
        
        @app.post("/concat")
        async def concat_videos(paths: List[str]):
            result = await service.concat_videos_async(paths, "output.mp4")
            return {"success": result.success}
    """
    
    def __init__(
        self,
        config: Optional[FFmpegConfig] = None,
        max_concurrent: int = 3,
        thread_pool_size: int = 2,
    ):
        """
        初始化服务
        
        Args:
            config: FFmpeg 配置
            max_concurrent: 最大并发处理数（视频处理很消耗资源，建议设小）
            thread_pool_size: 线程池大小
        """
        self.config = config or FFmpegConfig()
        self.client: Optional[FFmpegClient] = None
        self.max_concurrent = max_concurrent
        
        # 并发控制信号量
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        # 线程池
        self._thread_pool = ThreadPoolExecutor(
            max_workers=thread_pool_size,
            thread_name_prefix="ffmpeg_"
        )
    
    @property
    def semaphore(self) -> asyncio.Semaphore:
        """获取信号量（懒加载）"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore
    
    def init(self) -> bool:
        """
        初始化服务
        
        Returns:
            是否初始化成功
        """
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
    
    # ==================== 同步方法 ====================
    
    def get_video_info(self, video_path: str) -> VideoInfo:
        """获取视频信息（同步）"""
        self._ensure_client()
        return self.client.get_video_info(video_path)
    
    def compare_videos(
        self, 
        video1_path: str, 
        video2_path: str
    ) -> VideoCompareResult:
        """比较两个视频是否兼容（同步）"""
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
        """拼接多个视频（同步）"""
        self._ensure_client()
        
        if len(video_paths) < 2:
            return ConcatResult(
                success=False,
                error_message="至少需要两个视频文件"
            )
        
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
        """不重新编码拼接视频（同步）"""
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
        """重新编码拼接视频（同步）"""
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
        """将音频文件作为视频的背景音乐（同步）"""
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
    
    # ==================== 异步方法（推荐在 Web 后端使用）====================
    
    async def get_video_info_async(self, video_path: str) -> VideoInfo:
        """获取视频信息（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.get_video_info(video_path)
            )
    
    async def compare_videos_async(
        self,
        video1_path: str,
        video2_path: str
    ) -> VideoCompareResult:
        """比较两个视频是否兼容（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.compare_videos(video1_path, video2_path)
            )
    
    async def concat_videos_async(
        self,
        video_paths: List[str],
        output_path: str,
        mode: Optional[ConcatMode] = None,
        auto_detect: bool = True,
        **kwargs
    ) -> ConcatResult:
        """拼接多个视频（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.concat_videos(
                    video_paths, output_path, mode, auto_detect, **kwargs
                )
            )
    
    async def concat_videos_copy_async(
        self,
        video_paths: List[str],
        output_path: str
    ) -> ConcatResult:
        """不重新编码拼接视频（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.concat_videos_copy(video_paths, output_path)
            )
    
    async def concat_videos_reencode_async(
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
        """重新编码拼接视频（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.concat_videos_reencode(
                    video_paths=video_paths,
                    output_path=output_path,
                    video_codec=video_codec,
                    audio_codec=audio_codec,
                    video_bitrate=video_bitrate,
                    audio_bitrate=audio_bitrate,
                    resolution=resolution,
                    fps=fps
                )
            )
    
    async def mix_audio_async(
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
        """将音频文件作为视频的背景音乐（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.mix_audio(
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
        """检查多个视频的兼容性"""
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
    
    async def check_compatibility_async(self, video_paths: List[str]) -> dict:
        """检查多个视频的兼容性（异步）"""
        loop = asyncio.get_event_loop()
        async with self.semaphore:
            return await loop.run_in_executor(
                self._thread_pool,
                lambda: self.check_compatibility(video_paths)
            )
    
    # ==================== 资源管理 ====================
    
    def close(self):
        """关闭服务，释放资源"""
        self._thread_pool.shutdown(wait=False)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.close()


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


def create_ffmpeg_service(
    config: Optional[FFmpegConfig] = None,
    max_concurrent: int = 3,
    thread_pool_size: int = 2,
) -> FFmpegService:
    """
    创建新的 FFmpeg 服务实例
    
    Args:
        config: 可选的自定义配置
        max_concurrent: 最大并发处理数（视频处理消耗大，建议 2-5）
        thread_pool_size: 线程池大小
    
    Returns:
        已初始化的 FFmpegService 实例
    """
    service = FFmpegService(
        config=config,
        max_concurrent=max_concurrent,
        thread_pool_size=thread_pool_size,
    )
    service.init()
    return service
