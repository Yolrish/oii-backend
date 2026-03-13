"""
统一日志工具

整合 Python 标准 logging 和 packages.log.LogService：
- get_logger(name): 获取标准 logger，用于开发调试（console 输出）
- get_log_service(): 获取 LogService 单例，用于持久化日志（OpenSearch 等）
- LogServiceHandler: 自动将 WARNING+ 级别日志桥接到 LogService

使用方式：
    from utils.logger import get_logger

    logger = get_logger(__name__)
    logger.debug("调试信息")          # 仅 console
    logger.info("一般信息")           # console
    logger.warning("警告")            # console + LogService（自动桥接）
    logger.error("错误")              # console + LogService（自动桥接）

如需主动写入持久化日志：
    from utils.logger import get_log_service

    svc = get_log_service()
    await svc.info_async("用户登录", service="auth", user_id="xxx")
"""

import logging
import sys
from typing import Optional

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_setup_done = False


class LogServiceHandler(logging.Handler):
    """
    桥接 Handler：将 WARNING 及以上级别的日志自动转发到 LogService

    仅在 LogService 已初始化且有 Provider 注册时才写入，
    否则静默跳过，不影响主业务。
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from packages.log import LogService, LogLevel

            svc = LogService.get_instance()
            if not svc._providers:
                return

            level = LogLevel.ERROR if record.levelno >= logging.ERROR else LogLevel.WARN
            # 使用 logger name 最后一段作为 service 标识
            service = record.name.rsplit(".", 1)[-1]
            msg = self.format(record)
            svc.log(msg, level=level, service=service)
        except Exception:
            pass


def setup_logging(
    level: int = logging.DEBUG,
    fmt: Optional[str] = None,
    enable_bridge: bool = True,
) -> None:
    """
    全局日志初始化（在 main.py 启动时调用一次）

    Args:
        level: 全局日志级别，默认 DEBUG
        fmt: 自定义格式字符串
        enable_bridge: 是否启用 LogService 桥接（WARNING+ 自动写入 OpenSearch）
    """
    global _setup_done
    if _setup_done:
        return

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt or _LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(console)

    # LogService 桥接 handler（WARNING+）
    if enable_bridge:
        bridge = LogServiceHandler()
        bridge.setLevel(logging.WARNING)
        bridge.setFormatter(logging.Formatter("%(name)s | %(message)s"))
        root.addHandler(bridge)

    # 降低第三方库噪音
    for noisy in ("httpx", "httpcore", "urllib3", "pymongo", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _setup_done = True


def get_logger(name: str) -> logging.Logger:
    """
    获取标准 logger

    如果 setup_logging 尚未调用，会自动初始化一次（保证任何时候都能用）。

    Args:
        name: logger 名称，通常传 __name__
    Returns:
        配置好的 logging.Logger
    """
    if not _setup_done:
        setup_logging()
    return logging.getLogger(name)


def get_log_service():
    """
    获取 LogService 单例（用于主动写入持久化日志）

    Returns:
        packages.log.LogService 实例
    """
    from packages.log import LogService
    return LogService.get_instance()
