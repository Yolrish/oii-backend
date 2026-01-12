"""
Repository 基类
提供通用的 CRUD 操作抽象
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from abc import ABC, abstractmethod

T = TypeVar("T")  # 模型类型
CreateSchema = TypeVar("CreateSchema")  # 创建 schema
UpdateSchema = TypeVar("UpdateSchema")  # 更新 schema


class BaseRepository(ABC, Generic[T, CreateSchema, UpdateSchema]):
    """
    Repository 抽象基类
    实际项目中会注入数据库 session
    """
    
    @abstractmethod
    async def get(self, id: int) -> Optional[T]:
        """根据 ID 获取单条记录"""
        pass
    
    @abstractmethod
    async def get_multi(
        self, 
        offset: int = 0, 
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """获取多条记录"""
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计记录数"""
        pass
    
    @abstractmethod
    async def create(self, obj_in: CreateSchema) -> T:
        """创建记录"""
        pass
    
    @abstractmethod
    async def update(self, id: int, obj_in: UpdateSchema) -> Optional[T]:
        """更新记录"""
        pass
    
    @abstractmethod
    async def delete(self, id: int) -> bool:
        """删除记录"""
        pass


class InMemoryRepository(BaseRepository[T, CreateSchema, UpdateSchema]):
    """
    内存存储的 Repository 实现
    用于演示和测试，实际项目中替换为数据库实现
    """
    
    def __init__(self, initial_data: Optional[List[Dict[str, Any]]] = None):
        self._data: List[Dict[str, Any]] = initial_data or []
        self._id_counter = len(self._data) + 1
    
    async def get(self, id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取单条记录"""
        for item in self._data:
            if item.get("id") == id:
                return item
        return None
    
    async def get_multi(
        self, 
        offset: int = 0, 
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取多条记录，支持过滤"""
        result = self._data
        
        # 应用过滤条件
        if filters:
            for key, value in filters.items():
                if value is not None:
                    result = [
                        item for item in result 
                        if item.get(key) == value
                    ]
        
        return result[offset:offset + limit]
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计记录数"""
        if not filters:
            return len(self._data)
        
        result = self._data
        for key, value in filters.items():
            if value is not None:
                result = [
                    item for item in result 
                    if item.get(key) == value
                ]
        return len(result)
    
    async def create(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """创建记录"""
        new_item = {
            "id": self._id_counter,
            **obj_in
        }
        self._data.append(new_item)
        self._id_counter += 1
        return new_item
    
    async def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新记录"""
        for item in self._data:
            if item.get("id") == id:
                for key, value in obj_in.items():
                    if value is not None:
                        item[key] = value
                return item
        return None
    
    async def delete(self, id: int) -> bool:
        """删除记录"""
        for i, item in enumerate(self._data):
            if item.get("id") == id:
                self._data.pop(i)
                return True
        return False
    
    async def search(
        self, 
        keyword: str, 
        fields: List[str],
        offset: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索记录"""
        keyword_lower = keyword.lower()
        result = []
        
        for item in self._data:
            for field in fields:
                value = item.get(field)
                if value and keyword_lower in str(value).lower():
                    result.append(item)
                    break
        
        return result[offset:offset + limit]

