"""OpenAlex scholarly-evidence adapter.

Searches scholarly works and converts the title + reconstructed abstract into
citable passages. Keyless public API (a ``mailto`` puts the caller in the polite
pool). Abstracts are returned as an inverted index and are reconstructed here.
"""

from __future__ import annotations

import httpx

from ..core.text import split_sentences, tokenize
from .base import EvidencePassage, SourceAdapter, SourceResult, now_iso


def abstract_from_inverted(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        for pos in positions:
            positioned.append((pos, word))
    positioned.sort(key=lambda p: p[0])
    return " ".join(word for _, word in positioned)


class OpenAlexAdapter(SourceAdapter):
    name = "openalex"
    kind = "evidence"
    access = "OpenAlex REST API, public, no key; polite pool via mailto"
    rate_limits = "100k requests/day; polite pool recommended"

    def __init__(self, *, user_agent: str, mailto: str | None = None,
                 timeout: float = 20.0, per_page: int = 5) -> None:
        self.endpoint = "https://api.openalex.org/works"
        self.user_agent = user_agent
        self.mailto = mailto
        self.timeout = timeout
        self.per_page = per_page

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    async def search(
        self, claim: str, queries: list[str], client: httpx.AsyncClient
    ) -> SourceResult:
        query = (queries[0] if queries else claim)[:380]
        params: dict[str, str] = {
            "search": query,
            "per-page": str(self.per_page),
            "select": "id,doi,title,display_name,publication_year,primary_location,abstract_inverted_index",
        }
        if self.mailto:
            params["mailto"] = self.mailto
        try:
            resp = await client.get(self.endpoint, params=params, headers=self._headers(),
                                    timeout=self.timeout)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as exc:  # noqa: BLE001
            return SourceResult(status="error", error=f"openalex failed: {exc}",
                                queries=[query], endpoint=self.endpoint)

        passages: list[EvidencePassage] = []
        stamp = now_iso()
        for work in results:
            title = work.get("title") or work.get("display_name") or ""
            if not title:
                continue
            loc = work.get("primary_location") or {}
            source_meta = (loc.get("source") or {}) if isinstance(loc, dict) else {}
            venue = source_meta.get("display_name") or "OpenAlex"
            url = loc.get("landing_page_url") or work.get("doi") or work.get("id") or ""
            year = work.get("publication_year")
            abstract = abstract_from_inverted(work.get("abstract_inverted_index"))

            body = abstract or title
            emitted = 0
            for sentence in split_sentences(body):
                if len(tokenize(sentence.text)) < 6:
                    continue
                passages.append(EvidencePassage(
                    text=sentence.text, source=self.name, title=title, url=url,
                    publisher=venue, published_at=str(year) if year else None,
                    page_id=work.get("id"), retrieved_at=stamp,
                ))
                emitted += 1
            if emitted == 0:
                passages.append(EvidencePassage(
                    text=f"{title} ({year})." if year else f"{title}.",
                    source=self.name, title=title, url=url, publisher=venue,
                    published_at=str(year) if year else None, page_id=work.get("id"),
                    retrieved_at=stamp, note="title-only record (no abstract available)",
                ))

        return SourceResult(
            passages=passages,
            status="ok" if passages else "empty",
            queries=[query],
            endpoint=self.endpoint,
        )
