"""DuckDuckGo-backed web search tool for research agents."""

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


def search_web(query: str, *, max_results: int | None = None) -> list[WebSearchResult]:
    """Return top web snippets. Failures yield an empty list."""

    if not settings.web_search_enabled:
        return []
    limit = max_results or settings.web_search_max_results
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    try:
        raw_results = DDGS().text(query, max_results=limit)
    except Exception:
        return []

    results: list[WebSearchResult] = []
    for item in raw_results or []:
        title = str(item.get("title") or "").strip()
        url = str(item.get("href") or item.get("link") or "").strip()
        snippet = str(item.get("body") or item.get("snippet") or "").strip()
        if title or snippet:
            results.append(WebSearchResult(title=title, url=url, snippet=snippet))
    return results


def format_web_sources(results: list[WebSearchResult]) -> str:
    if not results:
        return "(No live web results available.)"
    lines = []
    for index, item in enumerate(results, start=1):
        lines.append(f"{index}. {item.title}\n   URL: {item.url}\n   {item.snippet}")
    return "\n".join(lines)
