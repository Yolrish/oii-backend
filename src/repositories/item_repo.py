"""
物品 Repository
"""
from typing import Optional, List, Dict, Any

from repositories.base import InMemoryRepository


# 模拟数据
INITIAL_ITEMS = [
    {"id": 1, "name": "iPhone 15", "description": "Apple smartphone", "price": 999.0, "category": "electronics", "status": "active", "owner_id": 1},
    {"id": 2, "name": "MacBook Pro", "description": "Apple laptop", "price": 2499.0, "category": "electronics", "status": "active", "owner_id": 1},
    {"id": 3, "name": "T-Shirt", "description": "Cotton t-shirt", "price": 29.99, "category": "clothing", "status": "active", "owner_id": 2},
]


class ItemRepository(InMemoryRepository):
    """
    物品数据访问层
    """
    
    def __init__(self):
        super().__init__(initial_data=INITIAL_ITEMS.copy())
    
    async def get_by_owner(
        self, 
        owner_id: int,
        offset: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取某用户的物品"""
        return await self.get_multi(
            offset=offset,
            limit=limit,
            filters={"owner_id": owner_id}
        )
    
    async def get_by_category(
        self,
        category: str,
        offset: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """按分类获取物品"""
        return await self.get_multi(
            offset=offset,
            limit=limit,
            filters={"category": category}
        )
    
    async def search_items(
        self,
        keyword: str,
        category: Optional[str] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索物品"""
        # 先搜索
        results = await self.search(
            keyword=keyword,
            fields=["name", "description"],
            offset=0,
            limit=1000  # 先获取全部再过滤
        )
        
        # 再过滤
        if category:
            results = [i for i in results if i.get("category") == category]
        if status:
            results = [i for i in results if i.get("status") == status]
        
        return results[offset:offset + limit]
    
    async def count_by_filters(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """按条件统计数量"""
        if search:
            results = await self.search(
                keyword=search,
                fields=["name", "description"],
                offset=0,
                limit=10000
            )
        else:
            results = self._data
        
        if category:
            results = [i for i in results if i.get("category") == category]
        if status:
            results = [i for i in results if i.get("status") == status]
        
        return len(results)


# 单例实例
item_repository = ItemRepository()

