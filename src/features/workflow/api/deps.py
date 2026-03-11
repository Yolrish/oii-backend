"""
Workflow API 依赖：get_workflow_service

供 FastAPI Depends 使用；需在应用 lifespan 中将 WorkflowService 注入 app.state.workflow_service。
"""
from fastapi import Request, HTTPException, status


def get_workflow_service(request: Request):
    """
    获取 Workflow 服务实例（由 lifespan 注入到 app.state）
    """
    from ..services import WorkflowService
    svc = getattr(request.app.state, "workflow_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow service not initialized",
        )
    return svc
