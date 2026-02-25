"""
FFmpeg 工具模块使用示例

运行方式：
    cd src
    python -m packages.ffmpeg.example
"""
import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from packages.ffmpeg import (
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
    print("=" * 50)
    print("示例 1: 快速开始")
    print("=" * 50)
    
    # 方式1：创建新服务实例（推荐）
    service = create_ffmpeg_service()
    
    # 方式2：使用默认实例（懒加载）
    service = get_default_service()
    
    # 检查是否可用
    if service.is_available():
        print(f"FFmpeg 版本: {service.get_version()}")
    else:
        print("FFmpeg 不可用")
    print()


def example_custom_config():
    """自定义配置示例"""
    print("=" * 50)
    print("示例 2: 自定义配置")
    print("=" * 50)
    
    # 自定义配置
    config = FFmpegConfig(
        video_codec="libx264",
        video_bitrate="8000k",
        timeout=7200
    )
    
    # 创建自定义配置的服务（带并发控制）
    service = create_ffmpeg_service(
        config=config,
        max_concurrent=3,      # 最大并发处理数
        thread_pool_size=2,    # 线程池大小
    )
    
    print(f"服务创建成功，max_concurrent=3")
    print()


def example_get_video_info():
    """获取视频信息示例（同步）"""
    print("=" * 50)
    print("示例 3: 获取视频信息（同步）")
    print("=" * 50)
    
    service = create_ffmpeg_service()
    
    video_path = "input.mp4"
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"示例文件 {video_path} 不存在，跳过")
        print()
        return
    
    info = service.get_video_info(video_path)
    
    print(f"文件: {info.path}")
    print(f"时长: {info.duration:.2f}秒")
    print(f"分辨率: {info.resolution}")
    print(f"帧率: {info.fps:.2f}fps")
    print(f"视频编码: {info.video_codec}")
    print(f"音频编码: {info.audio_codec}")
    print(f"文件大小: {info.size / 1024 / 1024:.2f}MB")
    print()


async def example_get_video_info_async():
    """获取视频信息示例（异步）"""
    print("=" * 50)
    print("示例 4: 获取视频信息（异步）")
    print("=" * 50)
    
    service = create_ffmpeg_service()
    
    video_path = "input.mp4"
    
    if not os.path.exists(video_path):
        print(f"示例文件 {video_path} 不存在，跳过")
        print()
        return
    
    # 使用异步方法
    info = await service.get_video_info_async(video_path)
    
    print(f"文件: {info.path}")
    print(f"时长: {info.duration:.2f}秒")
    print(f"分辨率: {info.resolution}")
    print()


def example_concat_copy():
    """不重新编码拼接示例（同步）"""
    print("=" * 50)
    print("示例 5: 不重编码拼接（同步）")
    print("=" * 50)
    
    service = create_ffmpeg_service()
    
    videos = ["part1.mp4", "part2.mp4", "part3.mp4"]
    output = "output_copy.mp4"
    
    # 检查文件
    missing = [v for v in videos if not os.path.exists(v)]
    if missing:
        print(f"示例文件不存在: {missing}，跳过")
        print()
        return
    
    result = service.concat_videos_copy(videos, output)
    
    if result.success:
        print(f"拼接成功!")
        print(f"输出文件: {result.output_path}")
        print(f"总时长: {result.duration:.2f}秒")
        print(f"耗时: {result.execution_time:.2f}秒")
    else:
        print(f"拼接失败: {result.error_message}")
    print()


async def example_concat_async():
    """拼接视频示例（异步）"""
    print("=" * 50)
    print("示例 6: 拼接视频（异步）")
    print("=" * 50)
    
    service = create_ffmpeg_service()
    
    videos = ["part1.mp4", "part2.mp4"]
    output = "output_async.mp4"
    
    missing = [v for v in videos if not os.path.exists(v)]
    if missing:
        print(f"示例文件不存在: {missing}，跳过")
        print()
        return
    
    # 使用异步方法
    result = await service.concat_videos_async(
        video_paths=videos,
        output_path=output,
        auto_detect=True,
    )
    
    print(f"使用模式: {result.mode.value}")
    print(f"成功: {result.success}")
    print(f"耗时: {result.execution_time:.2f}秒")
    print()


async def example_concurrent_processing():
    """并发处理示例"""
    print("=" * 50)
    print("示例 7: 并发处理多个视频")
    print("=" * 50)
    
    # 创建服务，限制最大并发数为 2
    service = create_ffmpeg_service(max_concurrent=2)
    
    videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
    
    # 检查文件
    existing = [v for v in videos if os.path.exists(v)]
    if not existing:
        print("没有示例视频文件，演示并发控制逻辑")
        print("并发控制：即使同时发起多个请求，也只会同时处理 2 个")
        print()
        return
    
    import time
    start = time.time()
    
    # 并发获取多个视频信息
    tasks = [service.get_video_info_async(v) for v in existing]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed = time.time() - start
    
    print(f"处理 {len(existing)} 个视频，总耗时: {elapsed:.2f}秒")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"视频 {i+1}: 错误 - {result}")
        else:
            print(f"视频 {i+1}: {result.duration:.2f}秒")
    print()


def example_mix_audio():
    """混音示例（同步）"""
    print("=" * 50)
    print("示例 8: 添加背景音乐（同步）")
    print("=" * 50)
    
    service = create_ffmpeg_service()
    
    video_path = "video.mp4"
    audio_path = "bgm.mp3"
    output_path = "output_with_bgm.mp4"
    
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        print(f"示例文件不存在，跳过")
        print()
        return
    
    result = service.mix_audio(
        video_path=video_path,
        audio_path=audio_path,
        output_path=output_path,
        loop_audio=True,
        audio_volume=0.8
    )
    
    if result.success:
        print(f"混音成功!")
        print(f"音频是否循环: {result.audio_looped}")
        print(f"耗时: {result.execution_time:.2f}秒")
    else:
        print(f"混音失败: {result.error_message}")
    print()


async def example_mix_audio_async():
    """混音示例（异步）"""
    print("=" * 50)
    print("示例 9: 添加背景音乐（异步）")
    print("=" * 50)
    
    service = create_ffmpeg_service()
    
    video_path = "video.mp4"
    audio_path = "bgm.mp3"
    output_path = "output_with_bgm_async.mp4"
    
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        print(f"示例文件不存在，跳过")
        print()
        return
    
    # 使用异步方法
    result = await service.mix_audio_async(
        video_path=video_path,
        audio_path=audio_path,
        output_path=output_path,
        loop_audio=True,
        audio_volume=0.8
    )
    
    if result.success:
        print(f"混音成功!")
        print(f"耗时: {result.execution_time:.2f}秒")
    else:
        print(f"混音失败: {result.error_message}")
    print()


async def example_resource_management():
    """资源管理示例"""
    print("=" * 50)
    print("示例 10: 资源管理（上下文管理器）")
    print("=" * 50)
    
    # 使用上下文管理器自动管理资源
    async with create_ffmpeg_service() as service:
        if service.is_available():
            print(f"服务可用: {service.get_version()}")
        print("退出上下文时自动释放资源")
    
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 50)
    print("FFmpeg 模块使用示例")
    print("=" * 50 + "\n")
    
    # 同步示例
    example_quick_start()
    example_custom_config()
    example_get_video_info()
    example_concat_copy()
    example_mix_audio()
    
    # 异步示例
    print("\n" + "=" * 50)
    print("异步示例")
    print("=" * 50 + "\n")
    
    asyncio.run(example_get_video_info_async())
    asyncio.run(example_concat_async())
    asyncio.run(example_concurrent_processing())
    asyncio.run(example_mix_audio_async())
    asyncio.run(example_resource_management())
    
    print("=" * 50)
    print("所有示例执行完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
