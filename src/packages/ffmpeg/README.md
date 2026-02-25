# FFmpeg 工具模块

封装 FFmpeg 命令行调用，提供视频处理功能，支持 Web 后端高并发场景。

## 功能

- 获取视频信息
- 比较视频参数
- 视频拼接（不重编码/重编码）
- 视频混音（添加背景音乐）
- **异步 API** - 支持 FastAPI 等异步框架
- **并发控制** - 防止资源耗尽

## 快速开始

```python
from packages.ffmpeg import create_ffmpeg_service

# 创建服务
service = create_ffmpeg_service()

# 获取视频信息
info = service.get_video_info("video.mp4")
print(f"时长: {info.duration}秒, 分辨率: {info.resolution}")
```

### FastAPI 中使用（推荐异步 API）

```python
from fastapi import FastAPI
from packages.ffmpeg import create_ffmpeg_service

app = FastAPI()
ffmpeg = create_ffmpeg_service(max_concurrent=3)

@app.post("/video/info")
async def get_info(path: str):
    info = await ffmpeg.get_video_info_async(path)
    return {"duration": info.duration, "resolution": info.resolution}

@app.post("/video/concat")
async def concat(paths: list[str], output: str):
    result = await ffmpeg.concat_videos_async(paths, output)
    return {"success": result.success}
```

## API

### 创建服务

```python
# 方式1：创建新实例（推荐）
service = create_ffmpeg_service()

# 方式2：自定义配置 + 并发控制
from packages.ffmpeg import FFmpegConfig
config = FFmpegConfig(video_codec="libx265", video_bitrate="8000k")
service = create_ffmpeg_service(
    config=config,
    max_concurrent=3,      # 最大并发处理数（视频处理消耗大，建议 2-5）
    thread_pool_size=2,    # 线程池大小
)

# 方式3：使用默认实例（懒加载）
from packages.ffmpeg import get_default_service
service = get_default_service()
```

### 同步方法 vs 异步方法

| 同步方法 | 异步方法 | 说明 |
|----------|----------|------|
| `get_video_info()` | `get_video_info_async()` | 获取视频信息 |
| `compare_videos()` | `compare_videos_async()` | 比较视频 |
| `concat_videos()` | `concat_videos_async()` | 拼接视频 |
| `concat_videos_copy()` | `concat_videos_copy_async()` | 不重编码拼接 |
| `concat_videos_reencode()` | `concat_videos_reencode_async()` | 重编码拼接 |
| `mix_audio()` | `mix_audio_async()` | 混音 |
| `check_compatibility()` | `check_compatibility_async()` | 检查兼容性 |

> ⚠️ **注意**：在 FastAPI 等异步框架中，请使用 `*_async()` 方法，避免阻塞事件循环。

### 视频拼接

```python
# 同步方式
result = service.concat_videos(
    video_paths=["part1.mp4", "part2.mp4"],
    output_path="output.mp4"
)

# 异步方式（推荐）
result = await service.concat_videos_async(
    video_paths=["part1.mp4", "part2.mp4"],
    output_path="output.mp4"
)

# 不重编码拼接（要求视频参数一致）
result = await service.concat_videos_copy_async(["v1.mp4", "v2.mp4"], "out.mp4")

# 重编码拼接（可统一不同参数的视频）
result = await service.concat_videos_reencode_async(
    video_paths=["720p.mp4", "1080p.mp4"],
    output_path="output.mp4",
    resolution="1920x1080",
    fps=30
)
```

### 添加背景音乐

```python
# 同步方式
result = service.mix_audio(
    video_path="video.mp4",
    audio_path="bgm.mp3",
    output_path="output.mp4",
    loop_audio=True,
    audio_volume=0.8
)

# 异步方式（推荐）
result = await service.mix_audio_async(
    video_path="video.mp4",
    audio_path="bgm.mp3",
    output_path="output.mp4",
    loop_audio=True,
    audio_volume=0.8
)
```

### 其他功能

```python
# 比较视频兼容性
result = await service.compare_videos_async("v1.mp4", "v2.mp4")
print(f"兼容: {result.is_compatible}")

# 检查多视频兼容性
compat = await service.check_compatibility_async(["v1.mp4", "v2.mp4", "v3.mp4"])
print(f"推荐模式: {compat['recommended_mode'].value}")
```

## 并发控制

```python
# 创建服务时指定最大并发数
service = create_ffmpeg_service(max_concurrent=3)

# 即使 100 个请求同时调用，也只会同时处理 3 个视频
# 其余请求会排队等待
results = await asyncio.gather(
    service.concat_videos_async(paths1, "out1.mp4"),
    service.concat_videos_async(paths2, "out2.mp4"),
    service.concat_videos_async(paths3, "out3.mp4"),
    # ... 更多请求会排队
)
```

> **注意**：并发控制只对 `*_async()` 方法生效，同步方法不受限制。

## 资源管理

```python
# 使用上下文管理器（推荐）
async with create_ffmpeg_service() as service:
    result = await service.concat_videos_async(paths, output)

# 或手动关闭
service = create_ffmpeg_service()
try:
    result = await service.concat_videos_async(paths, output)
finally:
    service.close()
```

## 环境变量

| 变量 | 说明 |
|------|------|
| FFMPEG_PATH | FFmpeg 可执行文件路径 |
| FFPROBE_PATH | FFprobe 可执行文件路径 |
| FFMPEG_TEMP_DIR | 临时文件目录 |

## 配置项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| ffmpeg_path | ffmpeg | FFmpeg 路径 |
| ffprobe_path | ffprobe | FFprobe 路径 |
| timeout | 3600 | 超时时间（秒） |
| video_codec | libx264 | 视频编码器 |
| audio_codec | aac | 音频编码器 |
| video_bitrate | 5000k | 视频比特率 |
| audio_bitrate | 192k | 音频比特率 |
| max_concurrent | 3 | 最大并发处理数 |
| thread_pool_size | 2 | 线程池大小 |

## 目录结构

```
ffmpeg/
├── __init__.py          # 模块入口
├── configs/             # 配置
├── models/              # 数据模型
├── providers/           # FFmpeg 客户端
├── services/            # 服务层
├── example.py           # 使用示例
└── README.md
```
