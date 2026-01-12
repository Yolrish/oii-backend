"""
用户相关端点
"""
from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.deps import (
    require_auth, 
    get_pagination_params,
    get_user_service,
)
from services.user_service import UserService
from schemas.user import UserCreate, UserUpdate, UserResponse
from schemas.common import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    service: UserService = Depends(get_user_service)
):
    """
    获取用户列表
    """
    return await service.get_users(
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """
    根据ID获取单个用户
    """
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service)
):
    """
    创建新用户
    """
    try:
        return await service.create_user(user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user_id: str = Depends(require_auth),
    service: UserService = Depends(get_user_service)
):
    """
    更新用户信息（需要登录）
    """
    try:
        user = await service.update_user(user_id, user_in)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user_id: str = Depends(require_auth),
    service: UserService = Depends(get_user_service)
):
    """
    删除用户（需要登录）
    """
    deleted = await service.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return None
