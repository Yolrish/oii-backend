"""
物品/资源相关端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.v1.deps import (
    get_pagination_params,
    get_current_user_id,
    get_item_service,
)
from services.item_service import ItemService
from schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemStatus, ItemCategory
from schemas.common import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("", response_model=PaginatedResponse[ItemResponse])
async def get_items(
    pagination: PaginationParams = Depends(get_pagination_params),
    category: Optional[ItemCategory] = Query(None, description="按分类筛选"),
    status: Optional[ItemStatus] = Query(None, description="按状态筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    service: ItemService = Depends(get_item_service)
):
    """
    获取物品列表，支持筛选和搜索
    """
    return await service.get_items(
        page=pagination.page,
        page_size=pagination.page_size,
        category=category,
        status=status,
        search=search
    )


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    """
    根据ID获取单个物品
    """
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    return item


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_in: ItemCreate,
    user_id: Optional[str] = Depends(get_current_user_id),
    service: ItemService = Depends(get_item_service)
):
    """
    创建新物品
    """
    owner_id = int(user_id) if user_id else None
    return await service.create_item(item_in, owner_id=owner_id)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    service: ItemService = Depends(get_item_service)
):
    """
    更新物品信息
    """
    item = await service.update_item(item_id, item_in)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    """
    删除物品
    """
    deleted = await service.delete_item(item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    return None
