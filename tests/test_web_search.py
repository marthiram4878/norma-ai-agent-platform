"""Web search tool tests."""

from unittest.mock import MagicMock, patch

from app.tools.web_search import WebSearchResult, format_web_sources, search_web


def test_format_web_sources_empty() -> None:
    assert format_web_sources([]) == "(No live web results available.)"


def test_format_web_sources_lists_urls() -> None:
    text = format_web_sources(
        [
            WebSearchResult(
                title="Cafe market",
                url="https://example.com/cafes",
                snippet="Growing demand",
            )
        ]
    )
    assert "https://example.com/cafes" in text
    assert "Growing demand" in text


def test_search_web_disabled() -> None:
    with patch("app.tools.web_search.settings") as settings:
        settings.web_search_enabled = False
        assert search_web("coffee shops australia") == []


def test_search_web_returns_snippets() -> None:
    fake_instance = MagicMock()
    fake_instance.text.return_value = [
        {
            "title": "Cafe market",
            "href": "https://example.com/cafes",
            "body": "Growing demand",
        }
    ]
    fake_ddgs = MagicMock(return_value=fake_instance)

    with (
        patch("app.tools.web_search.settings") as settings,
        patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=fake_ddgs)}),
    ):
        settings.web_search_enabled = True
        settings.web_search_max_results = 5
        results = search_web("coffee")

    assert len(results) == 1
    assert results[0].title == "Cafe market"
    assert results[0].url == "https://example.com/cafes"
