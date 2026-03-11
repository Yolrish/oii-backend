"""
消息内存 LRU 缓存

缓存活跃 session 的消息列表，减少 MongoDB 查询。
使用 OrderedDict 实现 LRU 淘汰。
"""

from collections import OrderedDict
from typing import Dict, List, Optional

from ..models.models import ChatMessage


class MessageCache:
    """
    基于 LRU 的消息缓存

    - get: 命中时将该 session 移到最近位置
    - put/append: 写入缓存，超出容量时淘汰最久未使用的 session
    - invalidate: 主动清除某 session 的缓存
    """

    def __init__(self, max_size: int = 50):
        self._max_size = max_size
        # session_id -> List[ChatMessage]（按 seq 有序）
        self._cache: OrderedDict[str, List[ChatMessage]] = OrderedDict()

    def get(self, session_id: str) -> Optional[List[ChatMessage]]:
        """获取缓存的消息列表，命中时提升优先级"""
        if session_id not in self._cache:
            return None
        self._cache.move_to_end(session_id)
        return self._cache[session_id]

    def put(self, session_id: str, messages: List[ChatMessage]) -> None:
        """写入完整消息列表"""
        if session_id in self._cache:
            self._cache.move_to_end(session_id)
        self._cache[session_id] = list(messages)
        self._evict()

    def append(self, session_id: str, message: ChatMessage) -> None:
        """追加一条消息到缓存（若 session 已在缓存中）"""
        if session_id in self._cache:
            self._cache[session_id].append(message)
            self._cache.move_to_end(session_id)

    def invalidate(self, session_id: str) -> None:
        """清除某 session 的缓存"""
        self._cache.pop(session_id, None)

    def clear(self) -> None:
        """清空全部缓存"""
        self._cache.clear()

    def _evict(self) -> None:
        """超出容量时淘汰最久未使用的"""
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def size(self) -> int:
        return len(self._cache)
