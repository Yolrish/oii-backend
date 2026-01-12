"""
通用响应模型
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    """基础响应模型"""
    code: int = 0
    message: str = "success"


class DataResponse(ResponseBase, Generic[T]):
    """单条数据响应"""
    data: Optional[T] = None


class PaginatedResponse(ResponseBase, Generic[T]):
    """分页响应模型"""
    items: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    
    @property
    def total_pages(self) -> int:
        """总页数"""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

