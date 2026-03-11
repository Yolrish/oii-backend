"""
用户数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


def _new_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"


@dataclass
class User:
    """用户"""

    id: str = field(default_factory=_new_user_id)
    # Auth0 标识（sub 字段，如 auth0|xxx、google-oauth2|xxx）
    auth0_id: str = ""
    email: str = ""
    nickname: str = ""
    avatar: str = ""
    # 角色与权限
    role: str = UserRole.USER
    permissions: List[str] = field(default_factory=list)
    # 业务字段
    quota: int = 0
    subscription: str = "free"
    preferences: Dict[str, Any] = field(default_factory=dict)
    # 时间
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = field(default_factory=datetime.utcnow)
