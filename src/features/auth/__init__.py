"""
Auth 用户系统

基于 Auth0 的用户认证与管理：
- Token 验证（JWKS 公钥）
- 用户自动同步（Auth0 → MongoDB）
- 认证依赖注入（get_current_user）
"""

from .configs import AuthConfig, default_config
from .models import User, UserRole
from .services import UserService, create_user_service
from .api.deps import get_current_user, get_optional_user, require_admin

__all__ = [
    "AuthConfig",
    "default_config",
    "User",
    "UserRole",
    "UserService",
    "create_user_service",
    "get_current_user",
    "get_optional_user",
    "require_admin",
]

__version__ = "1.0.0"
