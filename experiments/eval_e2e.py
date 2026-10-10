"""End-to-end evaluation on a small, hand-labelled set of live claims.

This exercises the real pipeline: live source retrieval -> hybrid ranking -> NLI ->
aggregation. It requires network access and the models, so it is NOT part of the
offline test suite.

The set is deliberately small and human-reviewed; treat the numbers as indicative,
not as a general accuracy estimate.

Usage:
    python experiments/eval_e2e.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from _common import save_json  # noqa: E402
from app.schemas.models import AnalyzeRequest  # noqa: E402
from app.services.analyzer import Analyzer  # noqa: E402

CASES = [
    {"claim": "The Eiffel Tower is located in Paris.", "expect": "SUPPORTED"},
    {"claim": "The Great Wall of China is located in Japan.", "expect": "REFUTED"},
    {"claim": "The capital of Australia is Canberra.", "expect": "SUPPORTED"},
    {"claim": "The capital of Australia is Sydney.", "expect": "REFUTED"},
    {"claim": "Python was created by Guido van Rossum.", "expect": "SUPPORTED"},
    {"claim": "Mount Everest is the highest mountain above sea level on Earth.", "expect": "SUPPORTED"},
    {"claim": "The Amazon River is the longest river in the world by every measure.", "expect": "CONFLICTING_EVIDENCE"},
    {"claim": "Zorbax-9 was the first spacecraft to land on the Sun.", "expect": "INSUFFICIENT_EVIDENCE"},
]


async def main() -> None:
    analyzer = Analyzer()
    records = []
    for case in CASES:
        start = time.perf_counter()
        report = await analyzer.analyze(AnalyzeRequest(claim=case["claim"]))
        elapsed = (time.perf_counter() - start) * 1000
        claim = report.claims[0]
        records.append(
            {
                "claim": case["claim"],
                "expected": case["expect"],
                "actual": claim.status.value,
                "match": claim.status.value == case["expect"],
                "explanation": claim.explanation,
                "support_passages": claim.stats.support_passages,
                "contradict_passages": claim.stats.contradict_passages,
                "latency_ms": elapsed,
                "degraded": report.meta.degraded_mode,
            }
        )
        flag = "OK " if records[-1]["match"] else "MISS"
        print(f"[{flag}] {claim.status.value:22s} (expected {case['expect']}) :: {case['claim']}")

    matches = sum(1 for r in records if r["match"])
    payload = {
        "benchmark": "hand-labelled-live-claims",
        "n": len(records),
        "matches": matches,
        "accuracy": matches / len(records) if records else None,
        "records": records,
        "limitations": [
            "Small, hand-labelled set; indicative only, not a general accuracy estimate.",
            "Live sources change over time; results are not fully reproducible.",
        ],
    }
    path = save_json("eval_e2e.json", payload)
    print(f"\nWrote {path}: {matches}/{len(records)} matched")


if __name__ == "__main__":
    asyncio.run(main())
