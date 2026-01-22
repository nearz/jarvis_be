import asyncio

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..core.config import settings
from ..core.logging import get_logger


class DelayMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds artificial delay to requests for testing UI/UX.
    Only active when APP_ENV is 'development' or 'testing'.
    """

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.enabled_envs = {"development", "testing", "dev"}

    async def dispatch(self, request: Request, call_next):
        if (
            settings.APP_ENV.lower() in self.enabled_envs
            and settings.DELAY_SECONDS > 0
        ):
            self.logger.debug(
                "Adding %.2fs delay to %s %s",
                settings.DELAY_SECONDS,
                request.method,
                request.url.path,
            )
            await asyncio.sleep(settings.DELAY_SECONDS)

        response = await call_next(request)
        return response
