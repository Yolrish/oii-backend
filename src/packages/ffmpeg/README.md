# FFmpeg 工具模块

封装 FFmpeg 命令行调用，提供视频处理功能。

## 功能

- 获取视频信息
- 比较视频参数
- 视频拼接（不重编码/重编码）
- 视频混音（添加背景音乐）

## 快速开始

```python
from utils.ffmpeg import create_ffmpeg_service

# 创建服务
service = create_ffmpeg_service()

# 获取视频信息
info = service.get_video_info("video.mp4")
print(f"时长: {info.duration}秒, 分辨率: {info.resolution}")
```

## API

### 创建服务

```python
# 方式1：创建新实例（推荐）
service = create_ffmpeg_service()

# 方式2：自定义配置
from utils.ffmpeg import FFmpegConfig
config = FFmpegConfig(video_codec="libx265", video_bitrate="8000k")
service = create_ffmpeg_service(config)

# 方式3：使用默认实例（懒加载）
from utils.ffmpeg import get_default_service
service = get_default_service()
```

### 视频拼接

```python
# 自动检测模式（参数一致用 copy，否则 reencode）
result = service.concat_videos(
    video_paths=["part1.mp4", "part2.mp4"],
    output_path="output.mp4"
)

# 不重编码拼接（要求视频参数一致）
result = service.concat_videos_copy(["v1.mp4", "v2.mp4"], "out.mp4")

# 重编码拼接（可统一不同参数的视频）
result = service.concat_videos_reencode(
    video_paths=["720p.mp4", "1080p.mp4"],
    output_path="output.mp4",
    resolution="1920x1080",
    fps=30
)
```

### 添加背景音乐

```python
# 替换原音频
result = service.mix_audio(
    video_path="video.mp4",
    audio_path="bgm.mp3",
    output_path="output.mp4",
    loop_audio=True,      # 音乐不够长时循环
    audio_volume=0.8      # 音量 80%
)

# 混合原音频和背景音乐
result = service.mix_audio(
    video_path="video.mp4",
    audio_path="bgm.mp3",
    output_path="output.mp4",
    replace_original=False,
    audio_volume=0.3,     # 背景音乐 30%
    original_volume=0.7   # 原视频 70%
)
```

### 其他功能

```python
# 比较视频兼容性
result = service.compare_videos("v1.mp4", "v2.mp4")
print(f"兼容: {result.is_compatible}")

# 检查多视频兼容性
compat = service.check_compatibility(["v1.mp4", "v2.mp4", "v3.mp4"])
print(f"推荐模式: {compat['recommended_mode'].value}")
```

## 环境变量

| 变量 | 说明 |
|------|------|
| FFMPEG_PATH | FFmpeg 可执行文件路径 |
| FFPROBE_PATH | FFprobe 可执行文件路径 |
| FFMPEG_TEMP_DIR | 临时文件目录，未设置时使用系统默认 |

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
| temp_dir | 环境变量/系统默认 | 临时文件目录 |

## 目录结构

```
ffmpeg/
├── __init__.py          # 模块入口
├── configs/             # 配置
├── models/              # 数据模型
├── providers/           # FFmpeg 客户端
└── services/            # 服务层
```

