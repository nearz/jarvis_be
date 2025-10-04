import os
from langchain_core.tools import tool, BaseTool
from tavily import TavilyClient

_TOOLS_REGISTRY = []


def register_tool(func):
    decorated = tool(func)
    _TOOLS_REGISTRY.append(decorated)
    return decorated


@register_tool
def tavily_search(query: str) -> str:
    """
    Search the web using Tavily API for real-time information.

    Args:
        query: The search query string

    Returns:
        A formatted string containing search results with titles, URLs, and content snippets
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY environment variable not set. Please set your Tavily API key."

    try:
        tavily_client = TavilyClient(api_key=api_key)
        response = tavily_client.search(query, search_depth="advanced", max_results=5)

        if not response or "results" not in response:
            return f"No results found for query: {query}"

        results = []
        for result in response["results"]:
            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            content = result.get("content", "No content available")

            results.append(f"**{title}**\nURL: {url}\nContent: {content}\n")

        return f"Search results for '{query}':\n\n" + "\n".join(results)

    except Exception as e:
        return f"Error performing search: {str(e)}"


def get_tools() -> list[BaseTool]:
    return _TOOLS_REGISTRY.copy()
