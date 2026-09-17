"""
ResearchPilot AI — Web Search Module

Integrates with Tavily Search API for optional web context enrichment.
Returns clean, structured snippets suitable for RAG context injection.
"""

from tavily import TavilyClient

import config


def search_web(query: str, max_results: int = config.TAVILY_MAX_RESULTS) -> list[dict]:
    """
    Search the web using Tavily and return structured results.

    Each result dict contains:
        {
            "title": "...",
            "url": "https://...",
            "snippet": "...",
        }

    Returns an empty list if the API key is not configured or the search fails.
    """
    if not config.TAVILY_API_KEY:
        return []

    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

        results: list[dict] = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            })

        return results

    except Exception as e:
        print(f"[search] Tavily search failed: {e}")
        return []
