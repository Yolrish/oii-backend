"""
FFmpeg 工具模块使用示例
"""
from utils.ffmpeg import (
    create_ffmpeg_service,
    get_default_service,
    FFmpegConfig,
    FFmpegService,
    FFmpegClient,
    FFmpegClientConfig,
    ConcatMode,
)


def example_quick_start():
    """快速开始示例"""
    
    # 方式1：创建新服务实例（推荐）
    service = create_ffmpeg_service()
    
    # 方式2：使用默认实例（懒加载）
    service = get_default_service()
    
    # 检查是否可用
    if service.is_available():
        print(f"FFmpeg 版本: {service.get_version()}")


def example_custom_config():
    """自定义配置示例"""
    
    # 自定义配置
    config = FFmpegConfig(
        ffmpeg_path="/usr/local/bin/ffmpeg",
        video_codec="libx265",
        video_bitrate="8000k",
        timeout=7200
    )
    
    # 创建自定义配置的服务
    service = create_ffmpeg_service(config)
    
    # 或者手动创建
    service = FFmpegService(config)
    service.init()


def example_multiple_instances():
    """多实例示例"""
    
    # 可以创建多个不同配置的实例
    service_h264 = create_ffmpeg_service(FFmpegConfig(video_codec="libx264"))
    service_h265 = create_ffmpeg_service(FFmpegConfig(video_codec="libx265"))
    
    # 每个实例独立工作
    print(f"H264 服务可用: {service_h264.is_available()}")
    print(f"H265 服务可用: {service_h265.is_available()}")


def example_direct_client():
    """直接使用 Client 示例"""
    
    # 直接创建客户端（不使用服务层）
    config = FFmpegClientConfig(
        video_codec="libx264",
        video_bitrate="5000k"
    )
    client = FFmpegClient(config)
    
    if client.is_available():
        print(f"FFmpeg 版本: {client.get_version()}")


def example_get_video_info():
    """获取视频信息示例"""
    
    service = create_ffmpeg_service()
    
    video_path = "input.mp4"
    info = service.get_video_info(video_path)
    
    print(f"文件: {info.path}")
    print(f"时长: {info.duration:.2f}秒")
    print(f"分辨率: {info.resolution}")
    print(f"帧率: {info.fps:.2f}fps")
    print(f"视频编码: {info.video_codec}")
    print(f"音频编码: {info.audio_codec}")
    print(f"文件大小: {info.size / 1024 / 1024:.2f}MB")


def example_compare_videos():
    """比较视频参数示例"""
    
    service = create_ffmpeg_service()
    
    video1 = "video1.mp4"
    video2 = "video2.mp4"
    
    result = service.compare_videos(video1, video2)
    
    print(f"是否兼容: {result.is_compatible}")
    print(f"编码匹配: {result.codec_match}")
    print(f"分辨率匹配: {result.resolution_match}")
    print(f"帧率匹配: {result.fps_match}")
    print(f"音频匹配: {result.audio_match}")
    
    if result.differences:
        print("差异:")
        for diff in result.differences:
            print(f"  - {diff}")


def example_concat_copy():
    """不重新编码拼接示例"""
    
    service = create_ffmpeg_service()
    
    videos = ["part1.mp4", "part2.mp4", "part3.mp4"]
    output = "output_copy.mp4"
    
    result = service.concat_videos_copy(videos, output)
    
    if result.success:
        print(f"拼接成功!")
        print(f"输出文件: {result.output_path}")
        print(f"总时长: {result.duration:.2f}秒")
        print(f"耗时: {result.execution_time:.2f}秒")
    else:
        print(f"拼接失败: {result.error_message}")


def example_concat_reencode():
    """重新编码拼接示例"""
    
    service = create_ffmpeg_service()
    
    videos = ["video_720p.mp4", "video_1080p.mp4"]
    output = "output_reencode.mp4"
    
    result = service.concat_videos_reencode(
        video_paths=videos,
        output_path=output,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="5000k",
        audio_bitrate="192k",
        resolution="1920x1080",
        fps=30
    )
    
    if result.success:
        print(f"拼接成功!")
        print(f"耗时: {result.execution_time:.2f}秒")
    else:
        print(f"拼接失败: {result.error_message}")


def example_auto_concat():
    """自动检测模式拼接示例"""
    
    service = create_ffmpeg_service()
    
    videos = ["video1.mp4", "video2.mp4"]
    output = "output_auto.mp4"
    
    # 自动检测模式
    result = service.concat_videos(
        video_paths=videos,
        output_path=output,
        auto_detect=True,
        # reencode 时使用的参数
        resolution="1920x1080",
        fps=30
    )
    
    print(f"使用模式: {result.mode.value}")
    print(f"成功: {result.success}")


def example_check_compatibility():
    """检查多个视频兼容性示例"""
    
    service = create_ffmpeg_service()
    
    videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
    
    compat = service.check_compatibility(videos)
    
    print(f"所有视频兼容: {compat['compatible']}")
    print(f"推荐模式: {compat['recommended_mode'].value}")
    
    if compat['all_differences']:
        print("发现的差异:")
        for diff in compat['all_differences']:
            print(f"  - {diff}")


def example_mix_audio_replace():
    """添加背景音乐（替换原音频）示例"""
    
    service = create_ffmpeg_service()
    
    result = service.mix_audio(
        video_path="video.mp4",
        audio_path="bgm.mp3",
        output_path="output_with_bgm.mp4",
        loop_audio=True,         # 音频不够长时循环
        replace_original=True,   # 替换原音频
        audio_volume=0.8         # 背景音乐音量 80%
    )
    
    if result.success:
        print(f"混音成功!")
        print(f"输出文件: {result.output_path}")
        print(f"音频是否循环: {result.audio_looped}")
        print(f"耗时: {result.execution_time:.2f}秒")
    else:
        print(f"混音失败: {result.error_message}")


def example_mix_audio_blend():
    """添加背景音乐（混合原音频）示例"""
    
    service = create_ffmpeg_service()
    
    result = service.mix_audio(
        video_path="video.mp4",
        audio_path="bgm.mp3",
        output_path="output_blended.mp4",
        loop_audio=True,          # 音频不够长时循环
        replace_original=False,   # 保留原音频
        audio_volume=0.3,         # 背景音乐音量 30%
        original_volume=0.7       # 原视频音量 70%
    )
    
    if result.success:
        print(f"混音成功!")
        print(f"总时长: {result.duration:.2f}秒")
    else:
        print(f"混音失败: {result.error_message}")


def example_mix_audio_no_loop():
    """添加背景音乐（不循环）示例"""
    
    service = create_ffmpeg_service()
    
    result = service.mix_audio(
        video_path="video.mp4",
        audio_path="short_bgm.mp3",
        output_path="output_no_loop.mp4",
        loop_audio=False,  # 音频不够长时不循环，后面会静音
        replace_original=True
    )
    
    if result.success:
        print(f"混音成功! 音频未循环: {not result.audio_looped}")


if __name__ == "__main__":
    example_quick_start()
