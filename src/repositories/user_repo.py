"""
用户 Repository
"""
from typing import Optional, List, Dict, Any

from repositories.base import InMemoryRepository


# 模拟数据
INITIAL_USERS = [
    {"id": 1, "username": "alice", "email": "alice@example.com", "nickname": "Alice", "is_active": True, "password_hash": "hashed_pw"},
    {"id": 2, "username": "bob", "email": "bob@example.com", "nickname": "Bob", "is_active": True, "password_hash": "hashed_pw"},
    {"id": 3, "username": "charlie", "email": "charlie@example.com", "nickname": None, "is_active": False, "password_hash": "hashed_pw"},
]


class UserRepository(InMemoryRepository):
    """
    用户数据访问层
    实际项目中会使用 SQLAlchemy 等 ORM
    """
    
    def __init__(self):
        super().__init__(initial_data=INITIAL_USERS.copy())
    
    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        for user in self._data:
            if user.get("username") == username:
                return user
        return None
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取用户"""
        for user in self._data:
            if user.get("email") == email:
                return user
        return None
    
    async def create(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户（添加默认字段）"""
        user_data = {
            **obj_in,
            "is_active": True,
            "password_hash": f"hashed_{obj_in.get('password', '')}",  # 模拟密码哈希
        }
        # 移除明文密码
        user_data.pop("password", None)
        return await super().create(user_data)
    
    async def get_active_users(
        self, 
        offset: int = 0, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取活跃用户"""
        return await self.get_multi(
            offset=offset,
            limit=limit,
            filters={"is_active": True}
        )


# 单例实例（实际项目中使用依赖注入）
user_repository = UserRepository()

