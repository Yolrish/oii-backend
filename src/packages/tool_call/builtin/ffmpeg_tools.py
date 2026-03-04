"""
FFmpeg 工具：将 FFmpeg 模块能力暴露给 tool-call
"""

from dataclasses import asdict
from typing import List, Optional

from ..registry import register_tool


@register_tool(
    name="get_video_info",
    description="获取视频文件的详细信息，包括时长、分辨率、编码格式、比特率等",
    parameters={
        "video_path": {
            "type": "string",
            "description": "视频文件路径",
        },
    },
    required=["video_path"],
)
def get_video_info(video_path: str) -> dict:
    """获取视频信息"""
    from packages.ffmpeg import create_ffmpeg_service

    svc = create_ffmpeg_service()
    info = svc.get_video_info(video_path)
    return asdict(info)


@register_tool(
    name="concat_videos",
    description="将多个视频拼接为一个视频文件。自动检测视频兼容性并选择拼接模式（copy 或 reencode）",
    parameters={
        "video_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "要拼接的视频文件路径列表，至少 2 个",
        },
        "output_path": {
            "type": "string",
            "description": "输出视频文件路径",
        },
    },
    required=["video_paths", "output_path"],
)
def concat_videos(video_paths: List[str], output_path: str) -> dict:
    """拼接视频"""
    from packages.ffmpeg import create_ffmpeg_service

    svc = create_ffmpeg_service()
    result = svc.concat_videos(video_paths, output_path)
    return asdict(result)


@register_tool(
    name="mix_audio",
    description="为视频添加背景音乐或替换音轨。支持音频循环、音量调节",
    parameters={
        "video_path": {
            "type": "string",
            "description": "视频文件路径",
        },
        "audio_path": {
            "type": "string",
            "description": "音频文件路径（BGM）",
        },
        "output_path": {
            "type": "string",
            "description": "输出视频文件路径",
        },
        "loop_audio": {
            "type": "boolean",
            "description": "音频不够长时是否循环，默认 true",
        },
        "audio_volume": {
            "type": "number",
            "description": "背景音乐音量（0.0~1.0），默认 1.0",
        },
        "original_volume": {
            "type": "number",
            "description": "原始音频音量（0.0~1.0），默认 0.0 表示替换",
        },
    },
    required=["video_path", "audio_path", "output_path"],
)
def mix_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    loop_audio: bool = True,
    audio_volume: float = 1.0,
    original_volume: float = 0.0,
) -> dict:
    """为视频混音"""
    from packages.ffmpeg import create_ffmpeg_service

    svc = create_ffmpeg_service()
    result = svc.mix_audio(
        video_path=video_path,
        audio_path=audio_path,
        output_path=output_path,
        loop_audio=loop_audio,
        audio_volume=audio_volume,
        original_volume=original_volume,
    )
    return asdict(result)


@register_tool(
    name="check_videos_compatibility",
    description="检查多个视频是否兼容（编码、分辨率、帧率等），并推荐拼接模式",
    parameters={
        "video_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "要检查的视频文件路径列表，至少 2 个",
        },
    },
    required=["video_paths"],
)
def check_videos_compatibility(video_paths: List[str]) -> dict:
    """检查视频兼容性"""
    from packages.ffmpeg import create_ffmpeg_service

    svc = create_ffmpeg_service()
    return svc.check_compatibility(video_paths)
