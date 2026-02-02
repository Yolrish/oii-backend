"""
数据模型模块

定义日志相关的数据结构，所有 Provider 共用：
- LogLevel: 日志级别枚举
- LogEntry: 日志条目
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class LogLevel(Enum):
    """日志级别枚举"""
    LOG = "log"      # 普通日志
    WARN = "warn"    # 警告
    ERROR = "error"  # 错误


@dataclass
class LogEntry:
    """
    日志条目模型
    
    所有 Provider 共用的标准日志格式
    """
    message: str                              # 日志消息（必填）
    level: LogLevel = LogLevel.LOG            # 日志级别
    service: str = "default"                  # 服务类别
    user: Optional[str] = None                # 用户名
    user_id: Optional[str] = None             # 用户 ID
    status_code: Optional[int] = None         # HTTP 状态码
    ip: Optional[str] = None                  # IP 地址
    metadata: Optional[Dict[str, Any]] = None # 扩展元数据
    timestamp: Optional[datetime] = None      # 时间戳
    index: Optional[str] = None               # 目标索引（用于 OpenSearch 等）
    
    def __post_init__(self):
        """初始化后自动设置时间戳"""
        if self.timestamp is None:
            self.timestamp = datetime.now().astimezone()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        doc = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value if isinstance(self.level, LogLevel) else self.level,
            "message": self.message,
            "service": self.service,
        }
        
        if self.user:
            doc["user"] = self.user
        if self.user_id:
            doc["user_id"] = self.user_id
        if self.status_code is not None:
            doc["status_code"] = self.status_code
        if self.ip:
            doc["ip"] = self.ip
        if self.metadata:
            doc["metadata"] = self.metadata
        
        return doc

