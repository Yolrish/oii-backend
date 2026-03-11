"""
Chat 会话管理模块

提供 session 隔离、上下文持久化（MongoDB + 内存缓存）、token 截断、HTTP API 及内部调用接口。
"""

from .configs import ChatConfig, default_config
from .models import Session, ChatMessage, SessionStatus
from .services import ChatService, SessionManager, create_chat_service

__all__ = [
    "ChatConfig",
    "default_config",
    "Session",
    "ChatMessage",
    "SessionStatus",
    "ChatService",
    "SessionManager",
    "create_chat_service",
]

__version__ = "1.0.0"
