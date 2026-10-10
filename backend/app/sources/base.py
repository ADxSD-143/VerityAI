"""Source-adapter contracts.

Each adapter declares how it is accessed (endpoint, auth, rate limits, failure
behavior) and returns either *original evidence* passages or a *publisher verdict*
(fact-check). Adapters must never invent a source or bypass access controls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx


def now_iso() -> str:
    """UTC timestamp at second precision, used for every retrieval record."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class EvidencePassage:
    text: str
    source: str
    title: str
    url: str
    publisher: str
    published_at: str | None = None
    page_id: str | None = None
    section: str | None = None
    retrieved_at: str = ""
    rank: int | None = None
    score: float | None = None
    note: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class FactCheckRecord:
    publisher: str
    publisher_verdict: str
    url: str
    claim_reviewed: str | None = None
    reviewed_at: str | None = None
    retrieved_at: str = ""
    source: str = "factcheck"


@dataclass
class SourceResult:
    passages: list[EvidencePassage] = field(default_factory=list)
    fact_checks: list[FactCheckRecord] = field(default_factory=list)
    status: str = "ok"  # ok | empty | error | skipped
    error: str | None = None
    queries: list[str] = field(default_factory=list)
    endpoint: str | None = None

    @property
    def n_results(self) -> int:
        return len(self.passages) + len(self.fact_checks)


class SourceAdapter(ABC):
    """Base class for every external evidence source."""

    name: str = "source"
    endpoint: str = ""
    kind: str = "evidence"  # or "factcheck"

    def describe(self) -> dict:
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "kind": self.kind,
            "access": getattr(self, "access", "public API, no key"),
            "rate_limits": getattr(self, "rate_limits", "documented by provider"),
        }

    @abstractmethod
    async def search(self, claim: str, queries: list[str], client: httpx.AsyncClient) -> SourceResult:
        """Return evidence for ``claim``. Must fail soft: return a SourceResult with
        status "error" instead of raising, so one broken source never breaks a request."""


def empty_result(adapter: SourceAdapter, status: str, error: str | None = None,
                 queries: list[str] | None = None) -> SourceResult:
    return SourceResult(
        status=status,
        error=error,
        queries=list(queries or []),
        endpoint=adapter.endpoint,
    )
