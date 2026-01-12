"""
物品相关 Schema
"""
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ItemStatus(str, Enum):
    """物品状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class ItemCategory(str, Enum):
    """物品分类枚举"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    OTHER = "other"


class ItemBase(BaseModel):
    """物品基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="物品名称")
    description: Optional[str] = Field(None, max_length=500, description="物品描述")
    price: float = Field(..., gt=0, description="价格")
    category: ItemCategory = Field(default=ItemCategory.OTHER, description="分类")


class ItemCreate(ItemBase):
    """创建物品请求"""
    pass


class ItemUpdate(BaseModel):
    """更新物品请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[ItemCategory] = None
    status: Optional[ItemStatus] = None


class ItemResponse(ItemBase):
    """物品响应模型"""
    id: int
    status: ItemStatus = ItemStatus.ACTIVE
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True

