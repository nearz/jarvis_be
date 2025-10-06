import logging
import os
from langchain_core.tools import tool, BaseTool
from tavily import TavilyClient

from .tavily_client import get_async_tavily_client, MissingApiKey

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
            return f"No results found for query: {query}"

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
        logging.error(e)
        return f"Error performing Tavily search: {e}"


def get_tools() -> list[BaseTool]:
    return _TOOLS_REGISTRY.copy()
