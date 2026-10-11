"""Opt-in network smoke tests.

These hit real external services and load real models, so they are excluded from the default
offline run (``addopts = -q -m "not live"``, which CI uses). Run them explicitly:

    pytest -q -m live

If the network is unavailable the tests skip rather than fail.
"""

import httpx
import pytest

pytestmark = pytest.mark.live

USER_AGENT = "VerityAI-smoke/0.1 (network smoke test; contact: adityanarayansd@gmail.com)"


async def test_live_wikipedia_adapter_returns_evidence_with_provenance():
    from app.sources.wikipedia import WikipediaAdapter

    adapter = WikipediaAdapter(lang="en", user_agent=USER_AGENT, max_pages=1, timeout=20.0)
    try:
        async with httpx.AsyncClient() as client:
            result = await adapter.search("Eiffel Tower Paris", ["Eiffel Tower Paris"], client)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"network unavailable: {exc}")

    assert result.status == "ok"
    assert result.passages
    passage = result.passages[0]
    assert passage.source == "wikipedia"
    assert passage.url.startswith("https://en.wikipedia.org/wiki/")
    assert passage.retrieved_at


async def test_live_wikinews_adapter_returns_evidence():
    from app.sources.wikipedia import WikinewsAdapter

    adapter = WikinewsAdapter(lang="en", user_agent=USER_AGENT, max_pages=1, timeout=20.0)
    try:
        async with httpx.AsyncClient() as client:
            result = await adapter.search("climate summit", ["climate summit"], client)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"network unavailable: {exc}")

    assert result.status in ("ok", "empty")
    if result.passages:
        assert result.passages[0].source == "wikinews"
        assert result.passages[0].url.startswith("https://en.wikinews.org/wiki/")


async def test_live_analyze_smoke_end_to_end():
    from app.schemas.models import AnalyzeRequest, Verdict
    from app.services.analyzer import Analyzer

    try:
        report = await Analyzer().analyze(
            AnalyzeRequest(claim="The Eiffel Tower is located in Paris.")
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"live analysis unavailable: {exc}")

    claim = report.claims[0]
    assert claim.status in set(Verdict)
    assert report.sources_queried
    # The pipeline must never fabricate evidence: every returned item has a source URL.
    for item in claim.supporting + claim.contradicting + claim.neutral:
        assert item.url
