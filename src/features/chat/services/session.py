"""
Session 管理

负责 session 的创建/获取/归档/删除，以及消息的读写（含缓存）。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..configs.config import ChatConfig
from ..models.models import Session, ChatMessage, SessionStatus
from ..providers.cache import MessageCache
from ..repositories import repository as repo


class SessionManager:
    """
    会话管理器

    管理 session 生命周期和消息读写，内部维护 LRU 缓存。
    """

    def __init__(self, db: Any, config: Optional[ChatConfig] = None):
        self.db = db
        self.config = config or ChatConfig.from_env()
        self.cache = MessageCache(max_size=self.config.cache_size)

    # ==================== Session CRUD ====================

    async def create_session(
        self,
        title: str = "",
        system_prompt: str = "",
        use_tools: bool = False,
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """创建新会话"""
        session = Session(
            user_id=user_id,
            title=title,
            system_prompt=system_prompt,
            use_tools=use_tools,
            metadata=metadata or {},
        )
        await repo.save_session(self.db, self.config.session_collection, session)
        # 初始化空消息缓存
        self.cache.put(session.id, [])
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return await repo.load_session(
            self.db, self.config.session_collection, session_id
        )

    async def update_session(self, session: Session) -> bool:
        """更新会话"""
        return await repo.update_session(
            self.db, self.config.session_collection, session
        )

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Session]:
        """列出会话"""
        return await repo.list_sessions(
            self.db, self.config.session_collection,
            user_id=user_id, status=status, limit=limit, offset=offset,
        )

    async def archive_session(self, session_id: str) -> bool:
        """归档会话"""
        session = await self.get_session(session_id)
        if not session:
            return False
        session.status = SessionStatus.ARCHIVED
        self.cache.invalidate(session_id)
        return await self.update_session(session)

    async def delete_session(self, session_id: str) -> bool:
        """删除会话及其所有消息"""
        self.cache.invalidate(session_id)
        await repo.delete_messages_by_session(
            self.db, self.config.message_collection, session_id
        )
        return await repo.delete_session(
            self.db, self.config.session_collection, session_id
        )

    # ==================== Message 读写 ====================

    async def get_messages(self, session_id: str) -> List[ChatMessage]:
        """获取消息（优先缓存）"""
        cached = self.cache.get(session_id)
        if cached is not None:
            return cached
        # 从 DB 加载
        messages = await repo.load_messages(
            self.db, self.config.message_collection, session_id
        )
        self.cache.put(session_id, messages)
        return messages

    async def get_messages_paginated(
        self,
        session_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ChatMessage]:
        """分页获取消息（直接查 DB，不走缓存）"""
        return await repo.load_messages(
            self.db, self.config.message_collection,
            session_id, limit=limit, offset=offset,
        )

    async def append_message(
        self,
        session: Session,
        message: ChatMessage,
    ) -> ChatMessage:
        """追加消息：写 DB + 更新缓存 + 更新 session 统计"""
        # 确定 seq
        message.session_id = session.id
        message.seq = session.message_count + 1
        session.message_count += 1
        session.updated_at = datetime.utcnow()

        # 写 DB
        await repo.save_message(self.db, self.config.message_collection, message)
        await repo.update_session(self.db, self.config.session_collection, session)

        # 更新缓存
        self.cache.append(session.id, message)

        return message

    async def update_session_tokens(
        self,
        session: Session,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """累加 session 的 token 消耗"""
        session.total_input_tokens += input_tokens
        session.total_output_tokens += output_tokens
        session.updated_at = datetime.utcnow()
        await repo.update_session(self.db, self.config.session_collection, session)
