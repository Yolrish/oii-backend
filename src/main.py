from contextlib import asynccontextmanager
from pathlib import Path
import sys

# 将 src 加入路径，便于从项目根运行 uvicorn src.main:app 或 python src/main.py 时解析 packages / api / core
_src_dir = Path(__file__).resolve().parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from fastapi import FastAPI

from packages.log import (
    create_default_log_service,
)
from api.v1.router import api_router
from core.mongodb import connect_mongodb, close_mongodb
from core.config import MongoDBConfig
from packages.workflow import create_workflow_service
from packages.workflow.configs import WorkflowConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时执行初始化，关闭时执行清理
    """
    # ===== 启动时执行 =====
    # log 服务初始化
    log_service = create_default_log_service()
    results = log_service.init(force=True)
    print(f"LOG服务初始化结果: {results}")

    # MongoDB 连接
    config = MongoDBConfig.from_env()
    await connect_mongodb(config)
    print(f"MongoDB 已连接，数据库: {config.db_name}")

    # Workflow 服务（注入 db，便于按需从 DB 加载）
    from core.mongodb import get_database
    workflow_config = WorkflowConfig.from_env()
    app.state.workflow_service = create_workflow_service(
        config=workflow_config,
        db=get_database(),
    )
    print(f"Workflow 服务已初始化，持久化: {workflow_config.persist_enabled}")

    yield

    # ===== 关闭时执行 =====
    await close_mongodb()
    print("服务正在关闭...")


app = FastAPI(
    title="AI Backend",
    description="AI 后端服务 API",
    version="1.0.0",
    lifespan=lifespan
)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """
    根路径 - 服务信息
    """
    return {
        "service": "AI Backend",
        "version": "1.0.0",
        "docs": "/docs"
    }