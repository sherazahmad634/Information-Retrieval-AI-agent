"""Web search tool backed by DuckDuckGo's public HTML endpoint.

No API key is required. Results are parsed from the lightweight ``html.duckduckgo.com``
endpoint to keep the dependency surface small.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.services.tools.base import Tool, ToolError, ToolResult
from app.utils.text import clean_text

logger = get_logger(__name__)

_DDG_URL = "https://html.duckduckgo.com/html/"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


class WebSearchTool(Tool):
    """Search the open web. Use sparingly; prefer document_search first."""

    name = "web_search"
    description = (
        "Search the public web for fresh information not available in the indexed "
        "corpus. Use this when the user explicitly asks for current events, recent "
        "facts, or topics that document_search returned no results for. Returns the "
        "top result titles, snippets, and URLs."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Web search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (1-10). Defaults to 5.",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, *, timeout: float = 8.0) -> None:
        self._timeout = timeout

    async def run(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        max_results = int(kwargs.get("max_results") or 5)
        if not isinstance(query, str) or not query.strip():
            raise ToolError("`query` is required.")

        try:
            html = await self._fetch(query)
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            raise ToolError(f"Web search request failed: {exc}") from exc

        results = self._parse_results(html, max_results=max_results)
        if not results:
            return ToolResult(
                content=f"Web search for '{query}' returned no parseable results.",
                data={"results": []},
            )

        lines = [f"Top {len(results)} web results for '{query}':"]
        for idx, r in enumerate(results, start=1):
            lines.append(f"[{idx}] {r['title']}\n{r['url']}\n{r['snippet']}")
        return ToolResult(content="\n\n".join(lines), data={"results": results})

    async def _fetch(self, query: str) -> str:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            follow_redirects=True,
        ) as client:
            resp = await client.post(_DDG_URL, data={"q": query})
            resp.raise_for_status()
            return resp.text

    @staticmethod
    def _parse_results(html: str, *, max_results: int) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict[str, str]] = []
        for result in soup.select("div.result"):
            title_el = result.select_one("a.result__a")
            snippet_el = result.select_one("a.result__snippet") or result.select_one(
                "div.result__snippet"
            )
            if not title_el:
                continue
            title = clean_text(title_el.get_text(" "))
            url = title_el.get("href", "")
            snippet = clean_text(snippet_el.get_text(" ")) if snippet_el else ""
            if not title or not url:
                continue
            items.append({"title": title, "url": str(url), "snippet": snippet})
            if len(items) >= max_results:
                break
        return items
