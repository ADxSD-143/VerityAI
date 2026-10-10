from app.analysis.aggregation import AggregateInput, aggregate
from app.schemas.models import Verdict


def test_two_independent_supporters_is_supported():
    result = aggregate(
        [AggregateInput("entailment", 0.9, 0), AggregateInput("entailment", 0.85, 1)], tau=0.5
    )
    assert result.status == Verdict.SUPPORTED
    assert result.limited_corroboration is False


def test_single_source_support_is_limited():
    result = aggregate([AggregateInput("entailment", 0.9, 0)], tau=0.5)
    assert result.status == Verdict.SUPPORTED
    assert result.limited_corroboration is True


def test_duplicate_source_passages_do_not_add_corroboration():
    result = aggregate(
        [AggregateInput("entailment", 0.9, 0), AggregateInput("entailment", 0.88, 0)], tau=0.5
    )
    assert result.status == Verdict.SUPPORTED
    assert result.limited_corroboration is True


def test_support_and_contradiction_is_conflicting():
    result = aggregate(
        [AggregateInput("entailment", 0.9, 0), AggregateInput("contradiction", 0.9, 1)], tau=0.5
    )
    assert result.status == Verdict.CONFLICTING_EVIDENCE


def test_two_independent_contradictors_is_refuted():
    result = aggregate(
        [AggregateInput("contradiction", 0.9, 0), AggregateInput("contradiction", 0.8, 1)], tau=0.5
    )
    assert result.status == Verdict.REFUTED


def test_weak_evidence_is_insufficient():
    result = aggregate(
        [AggregateInput("entailment", 0.2, 0), AggregateInput("neutral", 0.9, 1)], tau=0.5
    )
    assert result.status == Verdict.INSUFFICIENT_EVIDENCE


def test_empty_evidence_is_insufficient():
    assert aggregate([], tau=0.5).status == Verdict.INSUFFICIENT_EVIDENCE
