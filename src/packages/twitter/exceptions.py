"""
Twitter 模块异常定义
"""
from typing import Optional, Dict, Any


class TwitterError(Exception):
    """Twitter API 基础异常"""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(message)


class TwitterAuthError(TwitterError):
    """认证失败（401 / 403）"""
    pass


class TwitterRateLimitError(TwitterError):
    """触发速率限制（429）"""

    def __init__(self, message: str = "Twitter API 速率限制", reset_at: int = 0, **kwargs):
        self.reset_at = reset_at
        super().__init__(message, **kwargs)


class TwitterNotFoundError(TwitterError):
    """资源不存在（404）"""
    pass


class TwitterBadRequestError(TwitterError):
    """请求参数错误（400）"""
    pass


class TwitterConfigError(TwitterError):
    """配置缺失或不正确"""

    def __init__(self, message: str = "Twitter API 配置不完整"):
        super().__init__(message, status_code=0)
