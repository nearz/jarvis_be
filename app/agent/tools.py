import logging
import os
from langchain_core.tools import tool, BaseTool
from tavily import TavilyClient

from .tavily_client import get_async_tavily_client, MissingApiKey
from ..core.logging import get_logger

logger = get_logger(__name__)

_TOOLS_REGISTRY = []

TAVILY_MAX_RESULTS = 5
TAVILY_TIMEOUT = 15


def register_tool(func):
    decorated = tool(func)
    _TOOLS_REGISTRY.append(decorated)
    return decorated


# TODO: Should I consider adding max_results as param?
@register_tool
async def tavily_search(query: str) -> str:
    """
    Search the web using Tavily API for real-time information.

    Args:
        query: The search query string

    Returns:
        A formatted string containing search results with titles, URLs, and content snippets
    """
    try:
        client = get_async_tavily_client()
    except MissingApiKey as e:
        logger.exception("Tavily API key not set")
        return f"Error: {e}"

    try:
        resp = await client.search(
            query,
            search_depth="advanced",
            max_results=TAVILY_MAX_RESULTS,
            timeout=TAVILY_TIMEOUT,
        )

        results = (resp or {}).get("results", [])
        if not results:
            logger.warning("No results for query: %s", query)
            return f"No results found for query: {query}"

        logger.info("Tavily search complete | results count: %d", len(results))

        lines = [f"Search results for '{query}'"]
        for r in results[:5]:
            title = r.get("title", "No title")
            url = r.get("url", "No url")
            content = r.get("content", "").strip()
            if len(content) > 400:
                content = content[:397] + "..."
            lines.append(f"- **{title}**\n {url}\n {content}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Tavily search failed | query: %s", query)
        return f"Error performing Tavily search: {e}"


def get_tools() -> list[BaseTool]:
    return _TOOLS_REGISTRY.copy()
