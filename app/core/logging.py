import logging
import sys
from contextvars import ContextVar
from typing import Optional


request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def setup_logging(log_level: str = "INFO") -> None:
    log_format = "%(levelname)s | %(name)s | %(message)s"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Suppress from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)


class RequestLogger:
    """
    Custom logger that automatically includes request ID in all log messages.

    Usage:
        logger = RequestLogger(__name__)
        logger.info("Processing request")  # Output: [abc123] Processing request
    """

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)

    def _add_context(self, msg: str) -> str:
        request_id = request_id_var.get()
        if request_id:
            return f"[{request_id}] {msg}"
        return msg

    def debug(
        self,
        msg: str,
        *args,
        exc_info: bool = False,
        stack_info: bool = False,
        extra: Optional[dict] = None,
        **kwargs,
    ):
        self.logger.debug(
            self._add_context(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
            **kwargs,
        )

    def info(
        self,
        msg: str,
        *args,
        exc_info: bool = False,
        stack_info: bool = False,
        extra: Optional[dict] = None,
        **kwargs,
    ):
        self.logger.info(
            self._add_context(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
            **kwargs,
        )

    def warning(
        self,
        msg: str,
        *args,
        exc_info: bool = False,
        stack_info: bool = False,
        extra: Optional[dict] = None,
        **kwargs,
    ):
        self.logger.warning(
            self._add_context(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
            **kwargs,
        )

    def error(
        self,
        msg: str,
        *args,
        exc_info: bool = False,
        stack_info: bool = False,
        extra: Optional[dict] = None,
        **kwargs,
    ):
        self.logger.error(
            self._add_context(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
            **kwargs,
        )

    def critical(
        self,
        msg: str,
        *args,
        exc_info: bool = False,
        stack_info: bool = False,
        extra: Optional[dict] = None,
        **kwargs,
    ):
        self.logger.critical(
            self._add_context(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
            **kwargs,
        )

    def exception(self, msg: str, *args, **kwargs):
        """Call from an exception handler"""
        self.logger.exception(self._add_context(msg), *args, **kwargs)


def get_logger(name: str) -> RequestLogger:
    """
    Function to create a RequestLogger.

    Usage:
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Processing request")
    """
    return RequestLogger(name)
