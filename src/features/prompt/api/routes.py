"""
Prompt HTTP API

用户 prompt CRUD + 统一查询（含 builtin）
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from core.mongodb import get_database
from ..services.service import PromptService, create_prompt_service
from ..models.models import PromptSource

prompt_router = APIRouter(prefix="/prompts", tags=["Prompts"])


def _get_prompt_service() -> PromptService:
    db = get_database()
    return create_prompt_service(db)


# ==================== 请求/响应模型 ====================


class CreatePromptRequest(BaseModel):
    name: str = Field(..., min_length=1)
    template: str = Field(..., min_length=1)
    description: str = ""
    variables: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class UpdatePromptRequest(BaseModel):
    template: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class RenderPromptRequest(BaseModel):
    name: str = Field(..., min_length=1)
    variables: Dict[str, Any] = Field(default_factory=dict)


# ==================== 查询端点（多来源合并） ====================


@prompt_router.get("", summary="List all prompts")
async def list_prompts(
    source: Optional[str] = None,
    tag: Optional[str] = None,
    service: PromptService = Depends(_get_prompt_service),
) -> dict:
    """列出所有 prompt（builtin + user + external 合并）"""
    prompts = await service.list_all(source=source, tag=tag)
    return {
        "prompts": [_tpl_to_dict(p) for p in prompts],
        "count": len(prompts),
    }


@prompt_router.get("/{name}", summary="Get prompt by name")
async def get_prompt(
    name: str,
    service: PromptService = Depends(_get_prompt_service),
) -> dict:
    """按名称获取 prompt（优先级：user > builtin > external）"""
    tpl = await service.get(name)
    if not tpl:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _tpl_to_dict(tpl)


@prompt_router.post("/render", summary="Render prompt")
async def render_prompt(
    req: RenderPromptRequest,
    service: PromptService = Depends(_get_prompt_service),
) -> dict:
    """渲染 prompt 模板，返回替换变量后的文本"""
    try:
        text = await service.render(req.name, **req.variables)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"name": req.name, "rendered": text}


# ==================== 用户 CRUD ====================


@prompt_router.post("", summary="Create user prompt")
async def create_prompt(
    req: CreatePromptRequest,
    service: PromptService = Depends(_get_prompt_service),
) -> dict:
    tpl = await service.create(
        name=req.name,
        template=req.template,
        description=req.description,
        variables=req.variables,
        tags=req.tags,
    )
    return _tpl_to_dict(tpl)


@prompt_router.put("/{prompt_id}", summary="Update user prompt")
async def update_prompt(
    prompt_id: str,
    req: UpdatePromptRequest,
    service: PromptService = Depends(_get_prompt_service),
) -> dict:
    tpl = await service.update(
        prompt_id,
        template=req.template,
        description=req.description,
        variables=req.variables,
        tags=req.tags,
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _tpl_to_dict(tpl)


@prompt_router.delete("/{prompt_id}", summary="Delete user prompt")
async def delete_prompt(
    prompt_id: str,
    service: PromptService = Depends(_get_prompt_service),
) -> dict:
    ok = await service.delete(prompt_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"deleted": True}


# ==================== 工具 ====================


def _tpl_to_dict(tpl) -> dict:
    return {
        "id": tpl.id,
        "name": tpl.name,
        "template": tpl.template,
        "description": tpl.description,
        "source": tpl.source,
        "variables": [
            {"name": v.name, "description": v.description,
             "default": v.default, "required": v.required}
            for v in tpl.variables
        ],
        "tags": tpl.tags,
        "created_at": tpl.created_at.isoformat() if tpl.created_at else None,
        "updated_at": tpl.updated_at.isoformat() if tpl.updated_at else None,
    }
