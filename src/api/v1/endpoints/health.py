"""
健康检查端点
"""
from fastapi import APIRouter
from datetime import datetime

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
    # TODO: 检查数据库连接、Redis连接等
    checks = {
        "database": True,
        "cache": True,
    }
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
