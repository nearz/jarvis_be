from langchain_core.tools import tool, BaseTool

from .tavily_client import get_async_tavily_client, MissingApiKey
from ..core.logging import get_logger
from ..core.config import settings

logger = get_logger(__name__)

_TOOLS_REGISTRY = []


def register_tool(func):
    decorated = tool(func)
    _TOOLS_REGISTRY.append(decorated)
    return decorated


@register_tool
async def tavily_extract(url: str) -> str:
    """
    Extract web page content from the specified URL

    Args:
        url: the URL to extract content from

    Returns:
        A formatted string containing extraction results
    """
    if not url:
        return "Error: No URL provided for extraction"

    try:
        client = get_async_tavily_client()
    except MissingApiKey as e:
        logger.exception("Tavily API key not set")
        return f"Error: {e}"

    try:
        resp = await client.extract(
            urls=[url],
            include_images=False,
            extract_depth="advanced",
            format="markdown",
            timeout=settings.TAVILY_EXTRACT_TIMEOUT,
        )

        results = (resp or {}).get("results", [])
        if not results:
            logger.warning("No results for url extraction")
            return "No results for url extraction"

        logger.info("Tavily extraction complete")

        lines = ["Extraction Results: "]
        for r in results:
            title = r.get("title", "No Title")
            url = r.get("url", "No URL")
            content = r.get("raw_content", "").strip()
            lines.append(f"- **{title}**\n {url}\n {content}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Tavily extract failed")
        return f"Error performing Tavily extract: {e}"


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
            max_results=settings.TAVILY_MAX_RESULTS,
            timeout=settings.TAVILY_SEARCH_TIMEOUT,
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
