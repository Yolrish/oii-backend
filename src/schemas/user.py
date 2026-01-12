"""
用户相关 Schema
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: EmailStr
    nickname: Optional[str] = None


class UserCreate(UserBase):
    """创建用户请求"""
    password: str


class UserUpdate(BaseModel):
    """更新用户请求"""
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True

