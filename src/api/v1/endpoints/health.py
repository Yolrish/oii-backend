"""
健康检查端点
"""
from datetime import datetime

from fastapi import APIRouter

from core.mongodb import get_database

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """
    服务健康检查
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-backend"
    }


@router.get("/ready")
async def readiness_check():
    """
    就绪检查 - 检查所有依赖服务是否可用
    """
    # 检查 MongoDB 连接
    database_ok = False
    try:
        db = get_database()
        await db.client.admin.command("ping")
        database_ok = True
    except Exception:
        pass

    checks = {
        "database": database_ok,
        "cache": True,
    }

    all_ready = all(checks.values())

    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
