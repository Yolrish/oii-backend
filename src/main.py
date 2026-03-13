from contextlib import asynccontextmanager
from pathlib import Path
import sys

# 将 src 加入路径，便于从项目根运行 uvicorn src.main:app 或 python src/main.py 时解析 packages / api / core
_src_dir = Path(__file__).resolve().parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# 最先加载项目根 .env 到 os.environ，必须在任何其他项目导入之前
import load_env  # noqa: F401, E402

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import setup_logging, get_logger
from packages.log import create_default_log_service
from api.v1.router import api_router
from core.mongodb import connect_mongodb, close_mongodb
from core.config import MongoDBConfig
from features.workflow import create_workflow_service
from features.workflow.configs import WorkflowConfig

# 全局日志初始化（尽早调用）
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时执行初始化，关闭时执行清理
    """
    # ===== 启动时执行 =====
    # LogService 初始化（OpenSearch 等持久化日志）
    log_service = create_default_log_service()
    results = log_service.init(force=False)
    logger.info("LogService 初始化结果: %s", results)

    # MongoDB 连接
    config = MongoDBConfig.from_env()
    await connect_mongodb(config)
    logger.info("MongoDB 已连接，数据库: %s", config.db_name)

    # Workflow 服务（注入 db，便于按需从 DB 加载）
    from core.mongodb import get_database
    workflow_config = WorkflowConfig.from_env()
    app.state.workflow_service = create_workflow_service(
        config=workflow_config,
        db=get_database(),
    )
    logger.info("Workflow 服务已初始化，持久化: %s", workflow_config.persist_enabled)

    yield

    # ===== 关闭时执行 =====
    await close_mongodb()
    logger.info("服务正在关闭...")


app = FastAPI(
    title="AI Backend",
    description="AI 后端服务 API",
    version="1.0.0",
    lifespan=lifespan
)

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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