import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments"))

import annotation_tools as at  # noqa: E402
import eval_e2e_heldout as harness  # noqa: E402


def test_match_requires_gold_verdict_for_facts():
    assert harness._match("CHECKABLE_FACT", "SUPPORTED", "SUPPORTED") is True
    assert harness._match("CHECKABLE_FACT", "SUPPORTED", "REFUTED") is False
    assert harness._match("CHECKABLE_FACT", "", "SUPPORTED") is False


def test_match_forbids_true_false_for_non_facts():
    assert harness._match("OPINION_SUBJECTIVE", "", "INSUFFICIENT_EVIDENCE") is True
    assert harness._match("OPINION_SUBJECTIVE", "", "SUPPORTED") is False
    assert harness._match("ALLEGATION", "", "REFUTED") is False


def test_score_records_splits_factual_and_non_factual():
    records = [
        {"claim_type": "CHECKABLE_FACT", "match": True},
        {"claim_type": "CHECKABLE_FACT", "match": False},
        {"claim_type": "OPINION_SUBJECTIVE", "match": True},
        {"claim_type": "ALLEGATION", "match": False},
    ]
    summary = harness.score_records(records)
    assert summary["n"] == 4
    assert summary["factual_n"] == 2
    assert summary["non_factual_n"] == 2
    assert summary["factual_match"] == 0.5
    assert summary["non_factual_handling_match"] == 0.5
    assert summary["overall_match"] == 0.5
    assert summary["by_claim_type"]["CHECKABLE_FACT"] == {"n": 2, "match": 0.5}
    assert summary["overall_match_ci95"] is not None


def test_score_records_empty_is_safe():
    summary = harness.score_records([])
    assert summary["n"] == 0
    assert summary["overall_match"] is None


def test_blank_template_is_refused():
    rows, _ = at.load_annotations(REPO / "data" / "annotations" / "phase0_e2e_template.csv")
    report = at.validate(rows, schema="gold", min_held_out=60)
    assert report["errors"]
