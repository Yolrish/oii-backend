"""
Chat 配置
优先级：os.environ > chat 包 .env > 默认值
"""

import os
from dataclasses import dataclass

from load_env import load_module_env


@dataclass
class ChatConfig:
    """Chat 模块配置"""

    # MongoDB 集合名
    session_collection: str = "chat_sessions"
    message_collection: str = "chat_messages"
    # 内存 LRU 缓存：最多缓存多少个活跃 session 的消息
    cache_size: int = 50
    # 上下文 token 上限，超出时从最早消息开始截断
    max_context_tokens: int = 100000
    # token 估算：每个字符约占多少 token（粗估，中文约 1.5，英文约 0.25）
    chars_per_token: float = 1.5

    @classmethod
    def from_env(cls) -> "ChatConfig":
        """从环境变量加载配置"""
        load_module_env(__file__)
        return cls(
            session_collection=os.getenv(
                "CHAT_SESSION_COLLECTION", cls.session_collection
            ),
            message_collection=os.getenv(
                "CHAT_MESSAGE_COLLECTION", cls.message_collection
            ),
            cache_size=int(os.getenv("CHAT_CACHE_SIZE", str(cls.cache_size))),
            max_context_tokens=int(
                os.getenv("CHAT_MAX_CONTEXT_TOKENS", str(cls.max_context_tokens))
            ),
        )


default_config = ChatConfig()
