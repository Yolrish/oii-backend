# AI Backend

基于 FastAPI 的 AI 后端服务。

## 技术栈

- **框架**: FastAPI + Uvicorn
- **依赖管理**: uv
- **日志**: OpenSearch
- **视频处理**: FFmpeg

## 快速开始

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 安装开发依赖
uv sync --group dev
```

## 项目结构

```
src/
├── api/            # API 路由
├── core/           # 核心配置
├── middleware/     # 中间件
├── models/         # 数据模型
├── packages/       # 功能模块
│   ├── ffmpeg/     # 视频处理
│   └── log/        # 日志服务
├── repositories/   # 数据仓储
├── schemas/        # 请求/响应模式
├── services/       # 业务逻辑
├── utils/          # 工具函数
└── main.py         # 入口文件
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 常用命令

```bash
# 添加依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>

# 更新依赖
uv lock --upgrade && uv sync
```
