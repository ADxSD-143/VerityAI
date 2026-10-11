import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))

import annotation_tools as at  # noqa: E402


def _gold(case_id, text, claim_type="CHECKABLE_FACT", verdict="SUPPORTED", split="held_out"):
    return {
        "case_id": case_id,
        "claim_text": text,
        "claim_type_gold": claim_type,
        "verdict_gold": verdict,
        "reviewer": "owner",
        "split": split,
    }


def _clean_rows():
    return [
        _gold("a1", "The Eiffel Tower is located in Paris."),
        _gold("a2", "The Great Wall of China is located in Japan.", verdict="REFUTED"),
        _gold("a3", "Chocolate is the best ice cream flavor.", "OPINION_SUBJECTIVE", "NOT_VERIFIABLE"),
        _gold("b1", "Python was created by Guido van Rossum.", split="tuning"),
        _gold("b2", "Water is composed of hydrogen and oxygen.", split="tuning"),
    ]


def test_clean_gold_set_passes():
    report = at.validate(_clean_rows(), schema="gold", min_held_out=3)
    assert report["errors"] == []
    assert report["reviewed_counts"] == {"tuning": 2, "held_out": 3}


def test_too_few_reviewed_held_out_is_an_error_in_gold_mode():
    report = at.validate(_clean_rows(), schema="gold", min_held_out=60)
    assert any("reviewed held-out rows" in e for e in report["errors"])


def test_opinion_must_not_carry_true_false_verdict():
    rows = [_gold("a1", "Cats are better than dogs.", "OPINION_SUBJECTIVE", "SUPPORTED")]
    report = at.validate(rows, schema="gold", min_held_out=0)
    assert any("must not carry a SUPPORTED verdict" in e for e in report["errors"])


def test_invalid_claim_type_and_verdict_are_errors():
    rows = [_gold("a1", "Some claim here.", "FACTUAL", "MAYBE")]
    report = at.validate(rows, schema="gold", min_held_out=0)
    assert any("invalid claim type 'FACTUAL'" in e for e in report["errors"])
    assert any("invalid verdict 'MAYBE'" in e for e in report["errors"])


def test_duplicate_case_id_is_an_error():
    rows = [_gold("dup", "First claim text here."), _gold("dup", "Second distinct claim text.")]
    report = at.validate(rows, schema="gold", min_held_out=0)
    assert any("duplicate case_id 'dup'" in e for e in report["errors"])


def test_cross_split_near_duplicate_is_leakage():
    sentence = "The report says the bridge opened in 1932 after four years of construction work"
    rows = [
        _gold("x1", sentence, split="tuning"),
        _gold("x2", sentence, split="held_out"),
    ]
    report = at.validate(rows, schema="gold", min_held_out=0)
    assert report["cross_split_leakage"]
    assert any("cross-split near-duplicate leakage" in e for e in report["errors"])


def test_missing_required_column_is_an_error():
    rows = [{"case_id": "a1", "claim_text": "Paris is in France.", "claim_type_gold": "CHECKABLE_FACT"}]
    report = at.validate(rows, schema="gold", min_held_out=0)
    assert any("missing required columns" in e for e in report["errors"])


def test_select_returns_only_reviewed_rows():
    rows = _clean_rows()
    rows.append(_gold("c1", "An unreviewed row.", split="held_out"))
    rows[-1]["reviewer"] = ""
    selected = at.select(rows, split="held_out", schema="gold")
    assert {r["case_id"] for r in selected} == {"a1", "a2", "a3"}


def test_draft_schema_treats_short_held_out_as_warning():
    rows = [
        {
            "case_id": "P0-1",
            "claim_text": "The Eiffel Tower is located in Paris.",
            "proposed_claim_type": "CHECKABLE_FACT",
            "proposed_verdict": "SUPPORTED",
            "split": "held_out",
        }
    ]
    report = at.validate(rows, schema="draft", min_held_out=60)
    assert report["errors"] == []
    assert any("reviewed held-out rows" in w for w in report["warnings"])
