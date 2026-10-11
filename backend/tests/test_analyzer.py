import app.services.analyzer as analyzer_module
import pytest
from app.core.errors import ModelLoadError
from app.schemas.models import AnalyzeRequest, Verdict
from app.services.analyzer import Analyzer
from app.sources.base import EvidencePassage
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
async def test_single_weak_entailment_is_not_supported(monkeypatch):
    passages = [
        make_passage("A page that mentions the Sun and a spacecraft.", url="https://a.test/1")
    ]
    analyzer = _analyzer([FakeAdapter(passages)], [score("entailment", 0.55)])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(
        AnalyzeRequest(claim="Zorbax-9 was the first spacecraft to land on the Sun.")
    )

    claim = report.claims[0]
    assert claim.status == Verdict.INSUFFICIENT_EVIDENCE
    assert claim.limited_corroboration is False


@pytest.mark.asyncio
async def test_all_sources_failing_is_unable_to_assess(monkeypatch):
    analyzer = _analyzer([FakeAdapter([], status="error", error="boom")], [])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Some claim about something."))

    assert report.claims[0].status == Verdict.UNABLE_TO_ASSESS
    assert report.source_failures
    assert report.source_failures[0].error == "boom"


@pytest.mark.asyncio
async def test_one_source_failing_does_not_block_the_others(monkeypatch):
    good = FakeAdapter([make_passage("Paris is the capital of France.", url="https://a.test/1")])
    bad = FakeAdapter([], status="error", error="boom")
    analyzer = _analyzer([good, bad], [score("entailment", 0.9)])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Paris is the capital of France."))

    claim = report.claims[0]
    assert claim.status == Verdict.SUPPORTED
    assert len(report.sources_queried) == 2
    assert [record.source for record in report.source_failures] == ["fake"]


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


@pytest.mark.asyncio
async def test_nli_model_failure_degrades_to_unable_to_assess(monkeypatch):
    class _BrokenNLI:
        def predict_batch(self, pairs, batch_size: int = 16):  # noqa: ANN001
            raise ModelLoadError("nli model unavailable")

    passages = [make_passage("Paris is the capital of France.", url="https://a.test/1")]
    analyzer = _analyzer([FakeAdapter(passages)], [])
    analyzer._nli = _BrokenNLI()
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Paris is the capital of France."))

    claim = report.claims[0]
    assert claim.status == Verdict.UNABLE_TO_ASSESS
    assert report.meta.degraded_mode is True
    assert any("evidence assessment unavailable" in reason for reason in report.meta.degraded_reasons)


def _dated_passage(text, url, published_at):
    return EvidencePassage(
        text=text,
        source="fake",
        title="T",
        url=url,
        publisher="fake.test",
        page_id=url,
        published_at=published_at,
        retrieved_at="2026-01-01T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_undated_evidence_adds_a_recency_note(monkeypatch):
    passages = [make_passage("Paris is the capital of France.", url="https://a.test/1")]
    analyzer = _analyzer([FakeAdapter(passages)], [score("entailment", 0.9)])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Paris is the capital of France."))

    assert any("no publication date" in note for note in report.claims[0].claim_notes)


@pytest.mark.asyncio
async def test_dated_evidence_has_no_recency_note(monkeypatch):
    passages = [_dated_passage("Paris is the capital of France.", "https://a.test/1", "1999")]
    analyzer = _analyzer([FakeAdapter(passages)], [score("entailment", 0.9)])
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())

    report = await analyzer.analyze(AnalyzeRequest(claim="Paris is the capital of France."))

    assert not any("no publication date" in note for note in report.claims[0].claim_notes)
