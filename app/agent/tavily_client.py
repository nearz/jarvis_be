import os
from functools import lru_cache
from tavily import AsyncTavilyClient

from ..core.config import settings


class MissingApiKey(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_async_tavily_client() -> AsyncTavilyClient:
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        raise MissingApiKey("TAVILY_API_KEY not set.")
    return AsyncTavilyClient(api_key=api_key)
