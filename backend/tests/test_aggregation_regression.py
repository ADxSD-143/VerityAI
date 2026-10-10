"""Regression test for a documented aggregation false positive.

``docs/experiments/004-end-to-end.md`` records that the nonsense claim
"Zorbax-9 was the first spacecraft to land on the Sun." was reported SUPPORTED from a single
passage: one NLI entailment at or above ``tau`` (0.5) was enough to carry a verdict even though
it came from a single independent source. These tests pin the safeguard that prevents that mode:
a lone source must clear the higher ``tau_single`` bar to stand on its own.
"""

from app.analysis.aggregation import AggregateInput, aggregate
from app.schemas.models import Verdict


def test_single_passage_weak_entailment_does_not_yield_supported():
    result = aggregate([AggregateInput("entailment", 0.55, 0)], tau=0.5, tau_single=0.75)
    assert result.status != Verdict.SUPPORTED
    assert result.status == Verdict.INSUFFICIENT_EVIDENCE
    assert result.limited_corroboration is False


def test_boundary_at_tau_single_stands():
    result = aggregate([AggregateInput("entailment", 0.75, 0)], tau=0.5, tau_single=0.75)
    assert result.status == Verdict.SUPPORTED
    assert result.limited_corroboration is True
