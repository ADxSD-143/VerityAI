import app.services.analyzer as analyzer_module
import pytest
from app.schemas.models import AnalyzeRequest, Verdict
from app.services.analyzer import Analyzer
from conftest import FakeAdapter, FakeNLI, fake_retrieve_factory, make_passage, score


def _analyzer(adapters, scores):
    analyzer = Analyzer()
    analyzer.adapters = adapters
    analyzer._nli = FakeNLI(scores)
    return analyzer


@pytest.mark.asyncio
async def test_supported_flow_with_two_independent_sources(monkeypatch):
    passages = [
        make_passage("Paris is the capital of France.", url="https://a.test/1"),
        make_passage("The capital and largest city of France is Paris.", url="https://b.test/2"),
    ]
    analyzer = _analyzer([FakeAdapter(passages)], [score("entailment", 0.9), score("entailment", 0.85)])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Paris is the capital of France."))

    claim = report.claims[0]
    assert claim.status == Verdict.SUPPORTED
    assert claim.stats.support_passages == 2
    assert claim.limited_corroboration is False
    assert report.meta.degraded_mode is False
    assert report.sources_queried[0].source == "fake"
    assert claim.supporting[0].nli_label == "entailment"


@pytest.mark.asyncio
async def test_conflicting_evidence_flow(monkeypatch):
    passages = [
        make_passage("Paris is located in France.", url="https://a.test/1"),
        make_passage("Paris is located in Germany.", url="https://b.test/2"),
    ]
    analyzer = _analyzer(
        [FakeAdapter(passages)], [score("entailment", 0.9), score("contradiction", 0.9)]
    )
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Paris is located in France."))

    claim = report.claims[0]
    assert claim.status == Verdict.CONFLICTING_EVIDENCE
    assert claim.supporting and claim.contradicting


@pytest.mark.asyncio
async def test_no_evidence_is_insufficient(monkeypatch):
    analyzer = _analyzer([FakeAdapter([])], [])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Some claim about something."))

    assert report.claims[0].status == Verdict.INSUFFICIENT_EVIDENCE
    assert report.claims[0].supporting == []
    assert report.claims[0].contradicting == []


@pytest.mark.asyncio
async def test_all_sources_failing_is_unable_to_assess(monkeypatch):
    analyzer = _analyzer([FakeAdapter([], status="error", error="boom")], [])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Some claim about something."))

    assert report.claims[0].status == Verdict.UNABLE_TO_ASSESS
    assert report.source_failures
    assert report.source_failures[0].error == "boom"


@pytest.mark.asyncio
async def test_long_text_extracts_multiple_claims(monkeypatch):
    passages = [make_passage("Paris is the capital of France.", url="https://a.test/1")]
    analyzer = _analyzer([FakeAdapter(passages)], [score("entailment", 0.9), score("entailment", 0.9)])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    text = (
        "Paris is the capital of France. The city sits on the Seine river. "
        "It is a popular tourist destination for visitors."
    )
    report = await analyzer.analyze(AnalyzeRequest(text=text))

    assert report.input.kind == "text"
    assert len(report.claims) >= 2
