"""Fact-check (ClaimReview) adapter.

Queries the Google Fact Check Tools API, which aggregates ``ClaimReview`` markup
published by fact-checking organisations. What this source returns is a
**publisher verdict**, not original evidence, so results are surfaced separately
from VerityAI's own NLI assessment and never treated as ground truth.

Requires a free API key (``FACTCHECK_API_KEY``). Without it the adapter reports
``skipped`` and the rest of the pipeline continues unchanged.
"""

from __future__ import annotations

import httpx

from .base import FactCheckRecord, SourceAdapter, SourceResult, now_iso


class FactCheckAdapter(SourceAdapter):
    name = "factcheck"
    kind = "factcheck"
    access = "Google Fact Check Tools API; requires a free API key"
    rate_limits = "free tier quota; key-bound"

    def __init__(self, *, user_agent: str, api_key: str | None = None,
                 timeout: float = 20.0, page_size: int = 5) -> None:
        self.endpoint = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        self.user_agent = user_agent
        self.api_key = api_key
        self.timeout = timeout
        self.page_size = page_size

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    async def search(
        self, claim: str, queries: list[str], client: httpx.AsyncClient
    ) -> SourceResult:
        if not self.api_key:
            return SourceResult(
                status="skipped",
                error="FACTCHECK_API_KEY not configured; fact-check source disabled",
                queries=[claim], endpoint=self.endpoint,
            )
        params = {
            "query": claim[:400],
            "key": self.api_key,
            "pageSize": str(self.page_size),
            "languageCode": "en",
        }
        try:
            resp = await client.get(self.endpoint, params=params, headers=self._headers(),
                                    timeout=self.timeout)
            resp.raise_for_status()
            claims = resp.json().get("claims", [])
        except Exception as exc:  # noqa: BLE001
            return SourceResult(status="error", error=f"factcheck failed: {exc}",
                                queries=[claim], endpoint=self.endpoint)

        stamp = now_iso()
        records: list[FactCheckRecord] = []
        for entry in claims:
            for review in entry.get("claimReview", []):
                publisher = (review.get("publisher") or {}).get("name") or "unknown publisher"
                records.append(FactCheckRecord(
                    publisher=publisher,
                    publisher_verdict=review.get("textualRating") or "unrated",
                    url=review.get("url") or "",
                    claim_reviewed=entry.get("text"),
                    reviewed_at=review.get("reviewDate"),
                    retrieved_at=stamp,
                ))
        return SourceResult(
            fact_checks=records,
            status="ok" if records else "empty",
            queries=[claim],
            endpoint=self.endpoint,
        )
