"""Wikipedia / MediaWiki evidence adapter.

Primary keyless source. Uses the MediaWiki Action API:
  * ``list=search`` to find candidate articles for a query;
  * ``prop=extracts&explaintext=1`` to fetch plain-text article text.

Each sentence of the returned extract becomes an ``EvidencePassage`` carrying full
provenance (pageid, title, canonical URL, retrieval timestamp). Responses are
bounded (``exchars``, per-page and total passage caps) so a single huge article
cannot blow up the request.
"""

from __future__ import annotations

import asyncio

import httpx

from ..core.text import split_sentences, tokenize
from .base import EvidencePassage, SourceAdapter, SourceResult, now_iso

_MAX_QUERIES = 3
_MAX_TOTAL_PASSAGES = 240


class WikipediaAdapter(SourceAdapter):
    name = "wikipedia"
    kind = "evidence"
    access = "MediaWiki Action API, public, no key; descriptive User-Agent required"
    rate_limits = "polite use; one extract request per page, serialized with a short delay"

    def __init__(
        self,
        *,
        lang: str = "en",
        user_agent: str,
        max_pages: int = 4,
        max_passages_per_page: int = 60,
        timeout: float = 20.0,
    ) -> None:
        self.lang = lang
        self.endpoint = f"https://{lang}.wikipedia.org/w/api.php"
        self.user_agent = user_agent
        self.max_pages = max_pages
        self.max_passages_per_page = max_passages_per_page
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    async def search(
        self, claim: str, queries: list[str], client: httpx.AsyncClient
    ) -> SourceResult:
        queries = [q for q in queries if q.strip()][:_MAX_QUERIES] or [claim]
        titles: list[str] = []
        try:
            for q in queries:
                for title in await self._search_titles(client, q):
                    if title not in titles:
                        titles.append(title)
        except Exception as exc:  # noqa: BLE001 - fail soft, never break the request
            return SourceResult(
                status="error", error=f"search failed: {exc}", queries=queries,
                endpoint=self.endpoint,
            )

        titles = titles[: self.max_pages]
        passages: list[EvidencePassage] = []
        for title in titles:
            try:
                passages.extend(await self._fetch_extract(client, title))
            except Exception:  # noqa: BLE001 - skip an individual broken page
                continue
            if len(passages) >= _MAX_TOTAL_PASSAGES:
                break
            await asyncio.sleep(0.05)

        passages = passages[:_MAX_TOTAL_PASSAGES]
        return SourceResult(
            passages=passages,
            status="ok" if passages else "empty",
            queries=queries,
            endpoint=self.endpoint,
        )

    async def _search_titles(self, client: httpx.AsyncClient, query: str) -> list[str]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": str(max(3, self.max_pages)),
            "srnamespace": "0",
            "format": "json",
            "formatversion": "2",
        }
        resp = await client.get(
            self.endpoint, params=params, headers=self._headers(), timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return [r["title"] for r in data.get("query", {}).get("search", []) if r.get("title")]

    async def _fetch_extract(self, client: httpx.AsyncClient, title: str) -> list[EvidencePassage]:
        params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "exchars": "12000",
            "redirects": "1",
            "titles": title,
            "format": "json",
            "formatversion": "2",
        }
        resp = await client.get(
            self.endpoint, params=params, headers=self._headers(), timeout=self.timeout
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", [])
        if not pages:
            return []
        page = pages[0]
        if page.get("missing"):
            return []
        extract = page.get("extract") or ""
        if not extract.strip():
            return []
        resolved = page.get("title", title)
        url = f"https://{self.lang}.wikipedia.org/wiki/" + resolved.replace(" ", "_")
        pageid = str(page.get("pageid", "")) or None
        stamp = now_iso()

        out: list[EvidencePassage] = []
        for sentence in split_sentences(extract):
            if len(tokenize(sentence.text)) < 6:
                continue
            out.append(
                EvidencePassage(
                    text=sentence.text,
                    source=self.name,
                    title=resolved,
                    url=url,
                    publisher=f"{self.lang}.wikipedia.org",
                    page_id=pageid,
                    retrieved_at=stamp,
                )
            )
            if len(out) >= self.max_passages_per_page:
                break
        return out
