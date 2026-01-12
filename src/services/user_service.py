"""
用户 Service
业务逻辑层
"""
from typing import Optional, List, Dict, Any

from repositories.user_repo import UserRepository, user_repository
from schemas.user import UserCreate, UserUpdate, UserResponse
from schemas.common import PaginatedResponse


class UserService:
    """
    用户业务逻辑服务
    """
    
    def __init__(self, repo: UserRepository = None):
        self.repo = repo or user_repository
    
    async def get_user(self, user_id: int) -> Optional[UserResponse]:
        """
        获取单个用户
        """
        user = await self.repo.get(user_id)
        if not user:
            return None
        return UserResponse(**user)
    
    async def get_users(
        self, 
        page: int = 1, 
        page_size: int = 20
    ) -> PaginatedResponse[UserResponse]:
        """
        获取用户列表（分页）
        """
        offset = (page - 1) * page_size
        
        users = await self.repo.get_multi(offset=offset, limit=page_size)
        total = await self.repo.count()
        
        return PaginatedResponse(
            items=[UserResponse(**u) for u in users],
            total=total,
            page=page,
            page_size=page_size
        )
    
    async def create_user(self, user_in: UserCreate) -> UserResponse:
        """
        创建用户
        包含业务逻辑：检查用户名/邮箱是否重复
        """
        # 检查用户名是否已存在
        existing = await self.repo.get_by_username(user_in.username)
        if existing:
            raise ValueError(f"Username '{user_in.username}' already exists")
        
        # 检查邮箱是否已存在
        existing = await self.repo.get_by_email(user_in.email)
        if existing:
            raise ValueError(f"Email '{user_in.email}' already exists")
        
        # 创建用户
        user_data = user_in.model_dump()
        new_user = await self.repo.create(user_data)
        
        return UserResponse(**new_user)
    
    async def update_user(
        self, 
        user_id: int, 
        user_in: UserUpdate
    ) -> Optional[UserResponse]:
        """
        更新用户信息
        """
        # 检查用户是否存在
        existing = await self.repo.get(user_id)
        if not existing:
            return None
        
        # 如果更新邮箱，检查是否重复
        if user_in.email:
            email_user = await self.repo.get_by_email(user_in.email)
            if email_user and email_user.get("id") != user_id:
                raise ValueError(f"Email '{user_in.email}' already exists")
        
        # 更新
        update_data = user_in.model_dump(exclude_unset=True)
        updated = await self.repo.update(user_id, update_data)
        
        return UserResponse(**updated) if updated else None
    
    async def delete_user(self, user_id: int) -> bool:
        """
        删除用户
        """
        return await self.repo.delete(user_id)


# 单例服务实例
user_service = UserService()

