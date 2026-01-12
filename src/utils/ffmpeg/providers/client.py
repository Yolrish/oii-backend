"""
FFmpeg 命令行客户端
封装 subprocess 调用
"""
import subprocess
import json
import os
import tempfile
import time
import shutil
from dataclasses import dataclass
from typing import List, Optional, Tuple

from utils.ffmpeg.providers.exceptions import FFmpegError
from utils.ffmpeg.models.models import (
    VideoInfo,
    VideoCompareResult,
    ConcatResult,
    ConcatMode,
    MixAudioResult,
)


@dataclass
class FFmpegClientConfig:
    """FFmpeg 客户端配置"""
    
    # FFmpeg 可执行文件路径
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    
    # 超时设置（秒）
    timeout: int = 3600
    
    # 默认编码参数
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5000k"
    audio_bitrate: str = "192k"
    
    # 临时文件目录
    temp_dir: Optional[str] = None
    
    # 日志级别
    log_level: str = "error"
    
    def __post_init__(self):
        """初始化后解析路径"""
        self._resolve_paths()
    
    def _resolve_paths(self):
        """解析 ffmpeg 路径"""
        if self.ffmpeg_path == "ffmpeg":
            found = shutil.which("ffmpeg")
            if found:
                self.ffmpeg_path = found
        
        if self.ffprobe_path == "ffprobe":
            found = shutil.which("ffprobe")
            if found:
                self.ffprobe_path = found
    
    def get_temp_dir(self) -> str:
        """获取临时目录，未指定时使用系统默认"""
        return self.temp_dir or tempfile.gettempdir()


class FFmpegClient:
    """
    FFmpeg 命令行客户端
    封装 ffmpeg/ffprobe 命令调用
    """
    
    def __init__(self, config: Optional[FFmpegClientConfig] = None):
        self.config = config or FFmpegClientConfig()
    
    # ==================== 基础命令执行 ====================
    
    def _run_command(
        self, 
        cmd: List[str], 
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str]:
        """
        执行命令并返回结果
        
        Args:
            cmd: 命令列表
            timeout: 超时时间（秒）
        
        Returns:
            (return_code, stdout, stderr)
        """
        timeout = timeout or self.config.timeout
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise FFmpegError(f"命令执行超时: {' '.join(cmd[:3])}...")
        except FileNotFoundError:
            raise FFmpegError(f"找不到可执行文件: {cmd[0]}")
        except Exception as e:
            raise FFmpegError(f"命令执行失败: {e}")
    
    def _run_ffmpeg(self, args: List[str], timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """执行 ffmpeg 命令"""
        cmd = [self.config.ffmpeg_path, "-y", "-loglevel", self.config.log_level] + args
        return self._run_command(cmd, timeout)
    
    def _run_ffprobe(self, args: List[str]) -> Tuple[int, str, str]:
        """执行 ffprobe 命令"""
        cmd = [self.config.ffprobe_path] + args
        return self._run_command(cmd, timeout=60)
    
    # ==================== 视频信息获取 ====================
    
    def get_video_info(self, video_path: str) -> VideoInfo:
        """
        获取视频详细信息
        """
        if not os.path.exists(video_path):
            raise FFmpegError(f"视频文件不存在: {video_path}")
        
        args = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        returncode, stdout, stderr = self._run_ffprobe(args)
        
        if returncode != 0:
            raise FFmpegError(f"无法读取视频信息: {stderr}")
        
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            raise FFmpegError(f"无法解析视频信息: {stdout}")
        
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        info = VideoInfo(
            path=video_path,
            duration=float(format_info.get("duration", 0)),
            size=int(format_info.get("size", 0)),
            bitrate=int(format_info.get("bit_rate", 0)),
            format_name=format_info.get("format_name")
        )
        
        for stream in streams:
            codec_type = stream.get("codec_type")
            
            if codec_type == "video":
                info.video_codec = stream.get("codec_name")
                info.video_bitrate = int(stream.get("bit_rate", 0) or 0)
                info.width = int(stream.get("width", 0))
                info.height = int(stream.get("height", 0))
                info.pixel_format = stream.get("pix_fmt")
                
                fps_str = stream.get("r_frame_rate", "0/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    info.fps = float(num) / float(den) if float(den) > 0 else 0
                else:
                    info.fps = float(fps_str)
                    
            elif codec_type == "audio":
                info.audio_codec = stream.get("codec_name")
                info.audio_bitrate = int(stream.get("bit_rate", 0) or 0)
                info.sample_rate = int(stream.get("sample_rate", 0) or 0)
                info.channels = int(stream.get("channels", 0))
        
        return info
    
    # ==================== 视频比较 ====================
    
    def compare_videos(
        self, 
        video1_path: str, 
        video2_path: str,
        fps_tolerance: float = 0.1
    ) -> VideoCompareResult:
        """
        比较两个视频的关键参数是否一致
        """
        info1 = self.get_video_info(video1_path)
        info2 = self.get_video_info(video2_path)
        
        result = VideoCompareResult()
        differences = []
        
        # 比较视频编码
        result.codec_match = (info1.video_codec == info2.video_codec)
        if not result.codec_match:
            differences.append(f"视频编码不同: {info1.video_codec} vs {info2.video_codec}")
        
        # 比较分辨率
        result.resolution_match = (info1.width == info2.width and info1.height == info2.height)
        if not result.resolution_match:
            differences.append(f"分辨率不同: {info1.resolution} vs {info2.resolution}")
        
        # 比较帧率
        fps_diff = abs(info1.fps - info2.fps)
        result.fps_match = (fps_diff <= fps_tolerance)
        if not result.fps_match:
            differences.append(f"帧率不同: {info1.fps:.2f} vs {info2.fps:.2f}")
        
        # 比较音频
        audio_match_codec = (info1.audio_codec == info2.audio_codec)
        audio_match_sample = (info1.sample_rate == info2.sample_rate)
        audio_match_channels = (info1.channels == info2.channels)
        result.audio_match = audio_match_codec and audio_match_sample and audio_match_channels
        
        if not result.audio_match:
            if not audio_match_codec:
                differences.append(f"音频编码不同: {info1.audio_codec} vs {info2.audio_codec}")
            if not audio_match_sample:
                differences.append(f"采样率不同: {info1.sample_rate} vs {info2.sample_rate}")
            if not audio_match_channels:
                differences.append(f"声道数不同: {info1.channels} vs {info2.channels}")
        
        result.is_compatible = all([
            result.codec_match,
            result.resolution_match,
            result.fps_match,
            result.audio_match
        ])
        
        result.differences = differences
        return result
    
    # ==================== 视频拼接 - 不重新编码 ====================
    
    def concat_copy(
        self, 
        video_paths: List[str], 
        output_path: str
    ) -> ConcatResult:
        """
        不重新编码拼接视频（使用 concat demuxer）
        """
        start_time = time.time()
        result = ConcatResult(mode=ConcatMode.COPY)
        
        if len(video_paths) < 2:
            result.error_message = "至少需要两个视频文件"
            return result
        
        for path in video_paths:
            if not os.path.exists(path):
                result.error_message = f"视频文件不存在: {path}"
                return result
        
        temp_dir = self.config.get_temp_dir()
        list_file = os.path.join(temp_dir, f"concat_list_{int(time.time())}.txt")
        
        try:
            with open(list_file, 'w', encoding='utf-8') as f:
                for path in video_paths:
                    abs_path = os.path.abspath(path).replace("'", "'\\''")
                    f.write(f"file '{abs_path}'\n")
            
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_path
            ]
            
            returncode, stdout, stderr = self._run_ffmpeg(args)
            
            if returncode != 0:
                result.error_message = f"FFmpeg 执行失败: {stderr}"
                return result
            
            if os.path.exists(output_path):
                output_info = self.get_video_info(output_path)
                result.success = True
                result.output_path = output_path
                result.duration = output_info.duration
                result.size = output_info.size
            else:
                result.error_message = "输出文件未生成"
            
        except Exception as e:
            result.error_message = str(e)
            
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)
        
        result.execution_time = time.time() - start_time
        return result
    
    # ==================== 视频拼接 - 重新编码 ====================
    
    def concat_reencode(
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
        重新编码拼接视频（使用 filter_complex concat）
        """
        start_time = time.time()
        result = ConcatResult(mode=ConcatMode.REENCODE)
        
        if len(video_paths) < 2:
            result.error_message = "至少需要两个视频文件"
            return result
        
        for path in video_paths:
            if not os.path.exists(path):
                result.error_message = f"视频文件不存在: {path}"
                return result
        
        video_codec = video_codec or self.config.video_codec
        audio_codec = audio_codec or self.config.audio_codec
        video_bitrate = video_bitrate or self.config.video_bitrate
        audio_bitrate = audio_bitrate or self.config.audio_bitrate
        
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            n = len(video_paths)
            
            input_args = []
            for path in video_paths:
                input_args.extend(["-i", path])
            
            filter_parts = []
            
            for i in range(n):
                video_filters = []
                
                if resolution:
                    w, h = resolution.split("x")
                    video_filters.append(
                        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
                    )
                
                if fps:
                    video_filters.append(f"fps={fps}")
                
                if video_filters:
                    filter_parts.append(f"[{i}:v]{','.join(video_filters)}[v{i}]")
                else:
                    filter_parts.append(f"[{i}:v]null[v{i}]")
                
                filter_parts.append(f"[{i}:a]anull[a{i}]")
            
            concat_inputs = "".join([f"[v{i}][a{i}]" for i in range(n)])
            filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]")
            
            filter_complex = ";".join(filter_parts)
            
            args = input_args + [
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", video_codec,
                "-b:v", video_bitrate,
                "-c:a", audio_codec,
                "-b:a", audio_bitrate,
                output_path
            ]
            
            returncode, stdout, stderr = self._run_ffmpeg(args)
            
            if returncode != 0:
                result.error_message = f"FFmpeg 执行失败: {stderr}"
                return result
            
            if os.path.exists(output_path):
                output_info = self.get_video_info(output_path)
                result.success = True
                result.output_path = output_path
                result.duration = output_info.duration
                result.size = output_info.size
            else:
                result.error_message = "输出文件未生成"
            
        except Exception as e:
            result.error_message = str(e)
        
        result.execution_time = time.time() - start_time
        return result
    
    # ==================== 视频混音 - 添加背景音乐 ====================
    
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
        start_time = time.time()
        result = MixAudioResult()
        
        # 验证文件存在
        if not os.path.exists(video_path):
            result.error_message = f"视频文件不存在: {video_path}"
            return result
        
        if not os.path.exists(audio_path):
            result.error_message = f"音频文件不存在: {audio_path}"
            return result
        
        try:
            # 获取视频时长
            video_info = self.get_video_info(video_path)
            video_duration = video_info.duration
            
            # 获取音频时长
            audio_info = self._get_audio_info(audio_path)
            audio_duration = audio_info.get("duration", 0)
            
            # 判断是否需要循环
            need_loop = audio_duration < video_duration
            result.audio_looped = need_loop and loop_audio
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 使用配置默认值
            audio_codec = audio_codec or self.config.audio_codec
            audio_bitrate = audio_bitrate or self.config.audio_bitrate
            
            # 构建 ffmpeg 命令
            if replace_original or original_volume == 0:
                # 完全替换原音频
                args = self._build_replace_audio_args(
                    video_path=video_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    video_duration=video_duration,
                    loop_audio=loop_audio and need_loop,
                    audio_volume=audio_volume,
                    audio_codec=audio_codec,
                    audio_bitrate=audio_bitrate
                )
            else:
                # 混合原音频和背景音乐
                args = self._build_mix_audio_args(
                    video_path=video_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    video_duration=video_duration,
                    loop_audio=loop_audio and need_loop,
                    audio_volume=audio_volume,
                    original_volume=original_volume,
                    audio_codec=audio_codec,
                    audio_bitrate=audio_bitrate
                )
            
            returncode, stdout, stderr = self._run_ffmpeg(args)
            
            if returncode != 0:
                result.error_message = f"FFmpeg 执行失败: {stderr}"
                return result
            
            if os.path.exists(output_path):
                output_info = self.get_video_info(output_path)
                result.success = True
                result.output_path = output_path
                result.duration = output_info.duration
                result.size = output_info.size
            else:
                result.error_message = "输出文件未生成"
            
        except Exception as e:
            result.error_message = str(e)
        
        result.execution_time = time.time() - start_time
        return result
    
    def _get_audio_info(self, audio_path: str) -> dict:
        """获取音频文件信息"""
        args = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            audio_path
        ]
        
        returncode, stdout, stderr = self._run_ffprobe(args)
        
        if returncode != 0:
            raise FFmpegError(f"无法读取音频信息: {stderr}")
        
        try:
            data = json.loads(stdout)
            format_info = data.get("format", {})
            return {
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
            }
        except json.JSONDecodeError:
            raise FFmpegError(f"无法解析音频信息: {stdout}")
    
    def _build_replace_audio_args(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_duration: float,
        loop_audio: bool,
        audio_volume: float,
        audio_codec: str,
        audio_bitrate: str
    ) -> List[str]:
        """构建替换音频的 ffmpeg 参数"""
        args = []
        
        # 输入视频
        args.extend(["-i", video_path])
        
        # 输入音频（如需循环）
        if loop_audio:
            args.extend(["-stream_loop", "-1", "-i", audio_path])
        else:
            args.extend(["-i", audio_path])
        
        # 构建滤镜
        audio_filter = f"[1:a]volume={audio_volume}[bgm]"
        
        args.extend([
            "-filter_complex", audio_filter,
            "-map", "0:v",           # 使用视频的视频流
            "-map", "[bgm]",         # 使用处理后的音频
            "-c:v", "copy",          # 视频流直接复制
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-t", str(video_duration),  # 限制输出时长为视频时长
            "-shortest",
            output_path
        ])
        
        return args
    
    def _build_mix_audio_args(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_duration: float,
        loop_audio: bool,
        audio_volume: float,
        original_volume: float,
        audio_codec: str,
        audio_bitrate: str
    ) -> List[str]:
        """构建混合音频的 ffmpeg 参数"""
        args = []
        
        # 输入视频
        args.extend(["-i", video_path])
        
        # 输入音频（如需循环）
        if loop_audio:
            args.extend(["-stream_loop", "-1", "-i", audio_path])
        else:
            args.extend(["-i", audio_path])
        
        # 构建滤镜：调整音量并混合
        filter_complex = (
            f"[0:a]volume={original_volume}[orig];"
            f"[1:a]volume={audio_volume}[bgm];"
            f"[orig][bgm]amix=inputs=2:duration=first[aout]"
        )
        
        args.extend([
            "-filter_complex", filter_complex,
            "-map", "0:v",           # 使用视频的视频流
            "-map", "[aout]",        # 使用混合后的音频
            "-c:v", "copy",          # 视频流直接复制
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-t", str(video_duration),
            output_path
        ])
        
        return args
    
    # ==================== 工具方法 ====================
    
    def is_available(self) -> bool:
        """检查 ffmpeg 是否可用"""
        try:
            returncode, _, _ = self._run_command(
                [self.config.ffmpeg_path, "-version"], 
                timeout=10
            )
            return returncode == 0
        except:
            return False
    
    def get_version(self) -> Optional[str]:
        """获取 ffmpeg 版本"""
        try:
            returncode, stdout, _ = self._run_command(
                [self.config.ffmpeg_path, "-version"],
                timeout=10
            )
            if returncode == 0:
                first_line = stdout.split('\n')[0]
                return first_line
            return None
        except:
            return None

