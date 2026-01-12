"""
物品 Service
业务逻辑层
"""
from typing import Optional

from repositories.item_repo import ItemRepository, item_repository
from schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemStatus, ItemCategory
from schemas.common import PaginatedResponse


class ItemService:
    """
    物品业务逻辑服务
    """
    
    def __init__(self, repo: ItemRepository = None):
        self.repo = repo or item_repository
    
    async def get_item(self, item_id: int) -> Optional[ItemResponse]:
        """
        获取单个物品
        """
        item = await self.repo.get(item_id)
        if not item:
            return None
        return ItemResponse(**item)
    
    async def get_items(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[ItemCategory] = None,
        status: Optional[ItemStatus] = None,
        search: Optional[str] = None
    ) -> PaginatedResponse[ItemResponse]:
        """
        获取物品列表（支持筛选和搜索）
        """
        offset = (page - 1) * page_size
        
        # 构建过滤条件
        filters = {}
        if category:
            filters["category"] = category.value
        if status:
            filters["status"] = status.value
        
        # 搜索或普通查询
        if search:
            items = await self.repo.search_items(
                keyword=search,
                category=category.value if category else None,
                status=status.value if status else None,
                offset=offset,
                limit=page_size
            )
            total = await self.repo.count_by_filters(
                category=category.value if category else None,
                status=status.value if status else None,
                search=search
            )
        else:
            items = await self.repo.get_multi(
                offset=offset, 
                limit=page_size,
                filters=filters if filters else None
            )
            total = await self.repo.count(filters=filters if filters else None)
        
        return PaginatedResponse(
            items=[ItemResponse(**i) for i in items],
            total=total,
            page=page,
            page_size=page_size
        )
    
    async def create_item(
        self, 
        item_in: ItemCreate,
        owner_id: Optional[int] = None
    ) -> ItemResponse:
        """
        创建物品
        """
        item_data = item_in.model_dump()
        item_data["category"] = item_in.category.value
        item_data["status"] = ItemStatus.ACTIVE.value
        item_data["owner_id"] = owner_id
        
        new_item = await self.repo.create(item_data)
        return ItemResponse(**new_item)
    
    async def update_item(
        self, 
        item_id: int, 
        item_in: ItemUpdate
    ) -> Optional[ItemResponse]:
        """
        更新物品
        """
        existing = await self.repo.get(item_id)
        if not existing:
            return None
        
        update_data = {}
        for key, value in item_in.model_dump(exclude_unset=True).items():
            if value is not None:
                # 枚举类型转换为字符串
                update_data[key] = value.value if hasattr(value, 'value') else value
        
        updated = await self.repo.update(item_id, update_data)
        return ItemResponse(**updated) if updated else None
    
    async def delete_item(self, item_id: int) -> bool:
        """
        删除物品
        """
        return await self.repo.delete(item_id)
    
    async def get_user_items(
        self,
        owner_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResponse[ItemResponse]:
        """
        获取用户的物品列表
        """
        offset = (page - 1) * page_size
        
        items = await self.repo.get_by_owner(
            owner_id=owner_id,
            offset=offset,
            limit=page_size
        )
        total = await self.repo.count(filters={"owner_id": owner_id})
        
        return PaginatedResponse(
            items=[ItemResponse(**i) for i in items],
            total=total,
            page=page,
            page_size=page_size
        )


# 单例服务实例
item_service = ItemService()

