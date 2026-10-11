"""End-to-end evaluation on the human-reviewed held-out set.

This is the gate harness for Phase 0 (see ``docs/EVALUATION.md``). It refuses to compute any metric
unless the annotation file passes ``annotation_tools.validate`` in gold mode — that is, at least 60
reviewed held-out rows with no cross-split leakage. It never fills or guesses labels, and it never
turns model output into gold.

It drives the REAL pipeline (live sources + models), so it is not part of the offline test suite.

Usage:
    python experiments/eval_e2e_heldout.py --path data/annotations/phase0_e2e_template.csv
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import annotation_tools  # noqa: E402
from _common import bootstrap_mean_ci, save_json  # noqa: E402


def _match(claim_type: str, expected: str, actual: str) -> bool:
    """A factual row matches on verdict; a non-factual row matches only if it is NOT given a
    true/false verdict (opinions/predictions/allegations must not be asserted true or false)."""
    if claim_type == "CHECKABLE_FACT":
        return bool(expected) and actual == expected
    return actual not in ("SUPPORTED", "REFUTED")


def score_records(records: list[dict]) -> dict:
    """Summarise per-row results. Pure and deterministic (testable without the pipeline)."""
    factual = [r for r in records if r["claim_type"] == "CHECKABLE_FACT"]
    non_factual = [r for r in records if r["claim_type"] != "CHECKABLE_FACT"]

    def rate(rows: list[dict]) -> float | None:
        return sum(1 for r in rows if r["match"]) / len(rows) if rows else None

    by_type: dict[str, dict] = {}
    for record in records:
        bucket = by_type.setdefault(record["claim_type"], {"n": 0, "matched": 0})
        bucket["n"] += 1
        bucket["matched"] += int(record["match"])

    # Claim-type classification accuracy (Phase 2): predicted type vs the gold type.
    typed = [r for r in records if r.get("claim_type") and r.get("predicted_claim_type")]
    type_hits = [1.0 if r["predicted_claim_type"] == r["claim_type"] else 0.0 for r in typed]
    type_by_gold: dict[str, dict] = {}
    for record in typed:
        bucket = type_by_gold.setdefault(record["claim_type"], {"n": 0, "hit": 0})
        bucket["n"] += 1
        bucket["hit"] += int(record["predicted_claim_type"] == record["claim_type"])

    return {
        "n": len(records),
        "factual_n": len(factual),
        "non_factual_n": len(non_factual),
        "overall_match": rate(records),
        "overall_match_ci95": bootstrap_mean_ci(
            [1.0 if r["match"] else 0.0 for r in records], seed=42
        ),
        "factual_match": rate(factual),
        "non_factual_handling_match": rate(non_factual),
        "by_claim_type": {
            claim_type: {
                "n": values["n"],
                "match": values["matched"] / values["n"] if values["n"] else None,
            }
            for claim_type, values in sorted(by_type.items())
        },
        "claim_type_accuracy": (sum(type_hits) / len(type_hits)) if type_hits else None,
        "claim_type_accuracy_ci95": bootstrap_mean_ci(type_hits, seed=45),
        "claim_type_by_gold": {
            claim_type: {
                "n": values["n"],
                "accuracy": values["hit"] / values["n"] if values["n"] else None,
            }
            for claim_type, values in sorted(type_by_gold.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="data/annotations/phase0_e2e_template.csv")
    parser.add_argument("--min-held-out", type=int, default=60)
    parser.add_argument("--limit", type=int, default=0, help="0 = all held-out rows")
    args = parser.parse_args()

    rows, _ = annotation_tools.load_annotations(args.path)
    report = annotation_tools.validate(rows, schema="gold", min_held_out=args.min_held_out)
    annotation_tools._print_report(report)
    if report["errors"]:
        raise SystemExit(
            "Refusing to compute held-out metrics: annotation file has errors "
            "(unreviewed or under-sized held-out set)."
        )

    selected = annotation_tools.select(rows, split="held_out", schema="gold")
    if args.limit:
        selected = selected[: args.limit]
    if not selected:
        raise SystemExit("No reviewed held-out rows found.")

    from app.schemas.models import AnalyzeRequest
    from app.services.analyzer import Analyzer

    analyzer = Analyzer()
    records: list[dict] = []
    for row in selected:
        claim_type = (row.get("claim_type_gold") or "").strip()
        expected = (row.get("verdict_gold") or "").strip()
        start = time.perf_counter()
        result = asyncio.run(analyzer.analyze(AnalyzeRequest(claim=row["claim_text"])))
        elapsed_ms = (time.perf_counter() - start) * 1000
        claim = result.claims[0]
        actual = claim.status.value
        record = {
            "case_id": row.get("case_id"),
            "claim": row["claim_text"],
            "claim_type": claim_type,
            "predicted_claim_type": claim.claim_type,
            "expected": expected,
            "actual": actual,
            "match": _match(claim_type, expected, actual),
            "explanation": claim.explanation,
            "latency_ms": elapsed_ms,
            "degraded": result.meta.degraded_mode,
        }
        records.append(record)
        flag = "OK " if record["match"] else "MISS"
        print(f"[{flag}] {actual:22s} (expected {expected or claim_type}) :: {row['claim_text']}")

    payload = {
        "benchmark": "held-out-reviewed-claims",
        "annotation_file": args.path,
        "split": "held_out",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": score_records(records),
        "records": records,
        "limitations": [
            "Live sources change over time; results are not fully reproducible.",
            "The pipeline cannot yet emit NOT_VERIFIABLE or allegation-specific reports (Phase 2); "
            "non-factual rows are therefore expected to fail the handling check in Phase 0.",
            "Only reviewed rows are scored; unreviewed rows are excluded, never guessed.",
        ],
    }
    path = save_json("eval_e2e_heldout.json", payload)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
