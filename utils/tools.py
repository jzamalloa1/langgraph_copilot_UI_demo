import httpx, os
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from tavily import TavilyClient
from typing_extensions import Annotated, Literal

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Webpage content as markdown
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching content from {url}: {str(e)}"

@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query. Call this tool ONCE per request.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 3)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')

    Returns:
        Formatted search results with extracted content
    """
    # Use Tavily with include_answer for concise results
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
        include_answer=True,
    )

    # Build concise results using Tavily's extracted content
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]
        # Use Tavily's content extraction instead of fetching full pages
        content = result.get("content", "No content available")

        result_text = f"""## {title}
**URL:** {url}

{content}

---
"""
        result_texts.append(result_text)

    # Include Tavily's synthesized answer if available
    answer = search_results.get("answer", "")
    answer_section = f"**Summary:** {answer}\n\n" if answer else ""

    # Format final response with explicit completion signal
    response = f"""SEARCH COMPLETE - Found {len(result_texts)} result(s) for '{query}':

{answer_section}{chr(10).join(result_texts)}
---
SEARCH FINISHED. Extract the dates and values you need from above, then proceed to load_skill("historical-plotter"). Do NOT call tavily_search again."""

    return response