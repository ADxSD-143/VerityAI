"""Shared test fixtures.

The suite must run with **no network access and no model downloads**. Settings are
forced to safe test values before anything imports the app.
"""

from __future__ import annotations

import os
import tempfile

os.environ["VERITY_PRELOAD_MODELS"] = "false"
os.environ["VERITY_DEVICE"] = "cpu"
os.environ["VERITY_EMBED_CACHE_DIR"] = os.path.join(
    tempfile.gettempdir(), "verity-embed-cache-test"
)
os.environ.pop("FACTCHECK_API_KEY", None)

import pytest  # noqa: E402
from app.analysis.nli import NLIScore  # noqa: E402
from app.retrieval.pipeline import RankedPassage, RetrievalOutcome  # noqa: E402
from app.sources.base import EvidencePassage, SourceResult  # noqa: E402


class FakeAdapter:
    """Returns a fixed set of passages (or an error / empty result)."""

    name = "fake"
    kind = "evidence"
    endpoint = "https://fake.test/api"

    def __init__(self, passages=None, status="ok", error=None):
        self._passages = passages or []
        self._status = status if passages or status != "ok" else "empty"
        self._error = error

    async def search(self, claim, queries, client):  # noqa: ANN001
        return SourceResult(
            passages=list(self._passages),
            status=self._status,
            error=self._error,
            queries=list(queries),
            endpoint=self.endpoint,
        )


class FakeNLI:
    def __init__(self, scores):
        self._scores = scores

    def predict_batch(self, pairs, batch_size: int = 16):  # noqa: ANN001
        return self._scores[: len(pairs)]


def make_passage(text: str, *, url: str = "https://fake.test/a", source: str = "fake") -> EvidencePassage:
    return EvidencePassage(
        text=text,
        source=source,
        title="Fake title",
        url=url,
        publisher="fake.test",
        page_id=url,
        retrieved_at="2026-01-01T00:00:00+00:00",
    )


def score(label: str, value: float) -> NLIScore:
    probs = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
    probs[label] = value
    remaining = max(0.0, 1.0 - value)
    for other in probs:
        if other != label:
            probs[other] = remaining / 2
    return NLIScore(label=label, score=value, probs=probs)


def fake_retrieve_factory():
    def fake_retrieve(claim, passages, *, top_k=10, **kwargs):  # noqa: ANN001
        ranked = []
        for i, passage in enumerate(passages[:top_k]):
            ranked.append(
                RankedPassage(
                    index=i,
                    passage=passage,
                    bm25_rank=i + 1,
                    dense_rank=i + 1,
                    rrf_score=1.0 / (60 + i + 1),
                    rerank_score=None,
                    retrieval_score=1.0 / (60 + i + 1),
                )
            )
        return RetrievalOutcome(
            ranked=ranked, degraded=False, degraded_reasons=[], n_candidates=len(passages)
        )

    return fake_retrieve


@pytest.fixture
def anyio_backend():
    return "asyncio"
