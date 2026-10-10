"""Build the fixed FEVER evaluation sample.

Deterministic stratified sample of the official FEVER development split
(``fever`` / ``v1.0`` / ``validation``), seed 42. Writes the exact example ids,
claims, labels and gold evidence page titles to ``experiments/results/``.

Usage:
    python experiments/build_fever_sample.py --limit 500 --seed 42
"""

from __future__ import annotations

import argparse
from collections import Counter

from _common import (
    FEVER_LABELS,
    evidence_page_titles,
    save_json,
    stratified_sample,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    from datasets import load_dataset

    dataset = load_dataset("fever", "v1.0", split="validation")
    labels = list(dataset["label"])
    indices = stratified_sample(labels, args.limit, args.seed)
    if not indices:
        raise SystemExit("No examples selected - check the dataset schema.")

    examples = []
    for index in indices:
        row = dataset[int(index)]
        titles = evidence_page_titles(row.get("evidence"))
        examples.append(
            {
                "dataset_index": int(index),
                "fever_id": row.get("id"),
                "claim": row.get("claim"),
                "label": row.get("label"),
                "evidence_pages": titles,
                "evidence_raw": row.get("evidence"),
            }
        )

    distribution = Counter(example["label"] for example in examples)
    payload = {
        "dataset": "fever",
        "config": "v1.0",
        "split": "validation",
        "seed": args.seed,
        "requested": args.limit,
        "selected": len(examples),
        "label_distribution": dict(distribution),
        "examples": examples,
    }
    path = save_json("fever_sample.json", payload)
    print(f"Wrote {len(examples)} examples to {path}")
    print("Label distribution:", dict(distribution))
    assert set(distribution) <= set(FEVER_LABELS), "unexpected FEVER labels"


if __name__ == "__main__":
    main()
