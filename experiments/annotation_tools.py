"""Annotation tooling: validation and leakage checks for the Phase 0 sets.

The evaluation gate (see ``docs/EVALUATION.md`` §annotation and ``docs/READINESS.md``) requires a
human-reviewed held-out set with fixed splits. This module validates an annotation CSV before it is
used for any metric, and checks for claim and near-duplicate leakage across the tuning/held-out
split. It never fills in labels.

Two schemas are supported:

* ``gold``  — the reviewed template ``data/annotations/phase0_e2e_template.csv`` with the columns
  ``case_id, claim_text, claim_type_gold, verdict_gold, source_urls, source_dates, reviewer,
  ambiguous, rationale, split``.
* ``draft`` — the machine-proposed file ``data/annotations/phase0_candidates.csv``
  (``proposed_claim_type`` / ``proposed_verdict`` in place of the ``*_gold`` columns). A draft is
  never treated as gold.

Usage:
    python experiments/annotation_tools.py --path data/annotations/phase0_candidates.csv --schema draft
    python experiments/annotation_tools.py --path data/annotations/phase0_e2e_template.csv --schema gold
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

#: Claim/verdict enums defined in ``AGENTS.md`` / the output contract.
CLAIM_TYPES = (
    "CHECKABLE_FACT",
    "ALLEGATION",
    "OPINION_SUBJECTIVE",
    "PREDICTION",
    "UNCLEAR",
)
VERDICTS = (
    "SUPPORTED",
    "REFUTED",
    "CONFLICTING_EVIDENCE",
    "INSUFFICIENT_EVIDENCE",
    "UNABLE_TO_ASSESS",
    "NOT_VERIFIABLE",
    "NOT_APPLICABLE",
)
SPLITS = ("tuning", "held_out")

#: claim types that must never receive a SUPPORTED/REFUTED-style verdict.
NON_FACT_TYPES = {"OPINION_SUBJECTIVE", "PREDICTION", "UNCLEAR", "ALLEGATION"}

_FIELDS = {
    "gold": {
        "columns": ("case_id", "claim_text", "claim_type_gold", "verdict_gold", "reviewer", "split"),
        "claim_type": "claim_type_gold",
        "verdict": "verdict_gold",
        "reviewer": "reviewer",
    },
    "draft": {
        "columns": ("case_id", "claim_text", "proposed_claim_type", "proposed_verdict", "split"),
        "claim_type": "proposed_claim_type",
        "verdict": "proposed_verdict",
        "reviewer": None,
    },
}


def load_annotations(path: str | Path) -> tuple[list[dict], list[str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def duplicate_case_ids(rows: list[dict]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            continue
        if case_id in seen:
            duplicates.append(case_id)
        seen.add(case_id)
    return duplicates


def duplicate_claim_pairs(rows: list[dict]) -> list[tuple[str, str]]:
    """Pairs of case ids whose claim text is identical after normalisation."""
    seen: dict[str, str] = {}
    pairs: list[tuple[str, str]] = []
    for row in rows:
        key = _norm(row.get("claim_text"))
        case_id = (row.get("case_id") or "").strip()
        if not key:
            continue
        if key in seen:
            pairs.append((seen[key], case_id))
        else:
            seen[key] = case_id
    return pairs


def _char_shingles(text: str, n: int = 5) -> frozenset[str]:
    """Script-agnostic character n-grams.

    ``app.core.text.shingles`` tokenizes with a Latin-only regex, so non-Latin text (e.g.
    Devanagari) collapses to a single fallback gram — every such claim would look identical. For
    leakage detection we need a measure that works across scripts, so we use character n-grams here.
    """
    norm = _norm(text)
    if not norm:
        return frozenset()
    if len(norm) < n:
        return frozenset({norm})
    return frozenset(norm[i : i + n] for i in range(len(norm) - n + 1))


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    return inter / len(left | right) if inter else 0.0


def near_duplicate_pairs(texts: list[str], threshold: float = 0.8) -> list[tuple[int, int, float]]:
    grams = [_char_shingles(text) for text in texts]
    pairs: list[tuple[int, int, float]] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if not grams[i] or not grams[j]:
                continue
            score = _jaccard(grams[i], grams[j])
            if score >= threshold:
                pairs.append((i, j, round(score, 3)))
    return pairs


def cross_split_leakage(rows: list[dict], threshold: float = 0.8) -> list[tuple[str, str, float]]:
    """Near-duplicate claim pairs that straddle the tuning and held-out splits."""
    texts = [row.get("claim_text", "") for row in rows]
    leaks: list[tuple[str, str, float]] = []
    for i, j, score in near_duplicate_pairs(texts, threshold):
        left, right = rows[i].get("split"), rows[j].get("split")
        if {left, right} == set(SPLITS):
            leaks.append(((rows[i].get("case_id") or "?"), (rows[j].get("case_id") or "?"), score))
    return leaks


def _is_reviewed(row: dict, fields: dict) -> bool:
    if fields["reviewer"] and not (row.get(fields["reviewer"]) or "").strip():
        return False
    return bool((row.get(fields["claim_type"]) or "").strip())


def select(rows: list[dict], *, split: str, schema: str = "gold") -> list[dict]:
    """Reviewed rows for one split. Unreviewed rows are excluded, never guessed."""
    fields = _FIELDS[schema]
    return [
        row
        for row in rows
        if (row.get("split") or "").strip() == split and _is_reviewed(row, fields)
    ]


def validate(rows: list[dict], *, schema: str = "gold", min_held_out: int = 60) -> dict:
    fields = _FIELDS[schema]
    errors: list[str] = []
    warnings: list[str] = []

    required = fields["columns"]
    present = set(rows[0].keys()) if rows else set()
    missing_columns = [col for col in required if col not in present]
    if missing_columns:
        errors.append(f"missing required columns: {missing_columns}")

    split_counts = {split: 0 for split in SPLITS}
    reviewed_counts = {split: 0 for split in SPLITS}

    for index, row in enumerate(rows, start=2):  # line number in the CSV (header is line 1)
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            errors.append(f"line {index}: empty case_id")
        if not (row.get("claim_text") or "").strip():
            errors.append(f"line {index}: empty claim_text")

        split = (row.get("split") or "").strip()
        if split in split_counts:
            split_counts[split] += 1
        elif split:
            errors.append(f"line {index}: invalid split '{split}'")

        claim_type = (row.get(fields["claim_type"]) or "").strip()
        if claim_type and claim_type not in CLAIM_TYPES:
            errors.append(f"line {index}: invalid claim type '{claim_type}'")

        verdict = (row.get(fields["verdict"]) or "").strip()
        if verdict and verdict not in VERDICTS:
            errors.append(f"line {index}: invalid verdict '{verdict}'")
        if claim_type in NON_FACT_TYPES and verdict in ("SUPPORTED", "REFUTED"):
            errors.append(
                f"line {index}: {claim_type} must not carry a {verdict} verdict "
                "(opinions/allegations are not verifiable as true/false)"
            )
        if claim_type == "CHECKABLE_FACT" and split and _is_reviewed(row, fields) and not verdict:
            warnings.append(f"line {index}: reviewed CHECKABLE_FACT without a verdict")

        if _is_reviewed(row, fields) and split in reviewed_counts:
            reviewed_counts[split] += 1

    for case_id in duplicate_case_ids(rows):
        errors.append(f"duplicate case_id '{case_id}'")
    for left, right in duplicate_claim_pairs(rows):
        warnings.append(f"duplicate claim text: {left} == {right}")

    leaks = cross_split_leakage(rows)
    for left, right, score in leaks:
        errors.append(f"cross-split near-duplicate leakage: {left} ~ {right} (jaccard {score})")

    if reviewed_counts["held_out"] < min_held_out:
        message = (
            f"only {reviewed_counts['held_out']} reviewed held-out rows; "
            f"{min_held_out} required before held-out metrics"
        )
        (errors if schema == "gold" else warnings).append(message)

    return {
        "schema": schema,
        "total": len(rows),
        "split_counts": split_counts,
        "reviewed_counts": reviewed_counts,
        "duplicate_claim_pairs": duplicate_claim_pairs(rows),
        "cross_split_leakage": leaks,
        "errors": errors,
        "warnings": warnings,
    }


def _print_report(report: dict) -> None:
    print(f"schema={report['schema']} total={report['total']}")
    print(f"split counts: {report['split_counts']}")
    print(f"reviewed counts: {report['reviewed_counts']}")
    print(f"duplicate claim pairs: {len(report['duplicate_claim_pairs'])}")
    print(f"cross-split leakage: {len(report['cross_split_leakage'])}")
    for warning in report["warnings"]:
        print(f"  WARN  {warning}")
    for error in report["errors"]:
        print(f"  ERROR {error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--schema", choices=tuple(_FIELDS), default="gold")
    parser.add_argument("--min-held-out", type=int, default=60)
    args = parser.parse_args()

    rows, _ = load_annotations(args.path)
    report = validate(rows, schema=args.schema, min_held_out=args.min_held_out)
    _print_report(report)
    raise SystemExit(1 if report["errors"] else 0)


if __name__ == "__main__":
    main()
