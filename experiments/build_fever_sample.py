"""Build the fixed FEVER evaluation sample.

Deterministic stratified sample of claims from the official FEVER development set
(`fever` / `v1.0` / `labelled_dev`, the shared-task development split with evidence
annotations), seed 42. Writes the exact example ids, claims, labels and gold
evidence page titles to `experiments/results/`.

The `labelled_dev` split is stored *flattened* (one row per evidence annotation, so
claim ids repeat). Rows are grouped back into claims here, and FEVER's encoded page
titles (``Foo_-LRB-film-RRB-``) are decoded to ``Foo (film)``.

Usage:
    python experiments/build_fever_sample.py --limit 500 --seed 42
"""

from __future__ import annotations

import argparse
import random
from collections import Counter

from _common import decode_fever_title, save_json, stratified_sample


def group_claims(dataset) -> list[dict]:
    """Collapse the flattened rows into one record per claim, preserving order."""
    data = dataset.to_dict()
    claims: dict[object, dict] = {}
    for i in range(len(data["id"])):
        claim_id = data["id"][i]
        record = claims.get(claim_id)
        if record is None:
            record = {
                "fever_id": claim_id,
                "claim": data["claim"][i],
                "label": data["label"][i],
                "evidence_pages": [],
                "evidence_sentence_ids": {},
            }
            claims[claim_id] = record
        if record["label"] == "NOT ENOUGH INFO":
            continue
        title = decode_fever_title(data["evidence_wiki_url"][i])
        if not title:
            continue
        if title not in record["evidence_pages"]:
            record["evidence_pages"].append(title)
        sentence_id = data["evidence_sentence_id"][i]
        if isinstance(sentence_id, int) and sentence_id >= 0:
            ids = record["evidence_sentence_ids"].setdefault(title, [])
            if sentence_id not in ids:
                ids.append(sentence_id)
    return list(claims.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--split", default="labelled_dev")
    parser.add_argument(
        "--distractors",
        type=int,
        default=800,
        help="non-gold Wikipedia pages added to the retrieval corpus",
    )
    args = parser.parse_args()

    from datasets import load_dataset

    dataset = load_dataset("fever", "v1.0", split=args.split, trust_remote_code=True)
    claims = group_claims(dataset)
    if not claims:
        raise SystemExit("No claims parsed - check the dataset schema.")

    labels = [claim["label"] for claim in claims]
    indices = stratified_sample(labels, args.limit, args.seed)
    examples = []
    for index in indices:
        claim = claims[index]
        examples.append({**claim, "dataset_index": index})

    distribution = Counter(example["label"] for example in examples)

    gold_pages = {title for example in examples for title in example["evidence_pages"]}
    sampled_ids = {example["fever_id"] for example in examples}
    distractor_pool = sorted(
        {
            title
            for claim in claims
            if claim["fever_id"] not in sampled_ids
            for title in claim["evidence_pages"]
            if title not in gold_pages
        }
    )
    rng = random.Random(args.seed)
    distractors = rng.sample(distractor_pool, min(args.distractors, len(distractor_pool)))

    payload = {
        "dataset": "fever",
        "config": "v1.0",
        "split": args.split,
        "seed": args.seed,
        "requested": args.limit,
        "available_claims": len(claims),
        "selected": len(examples),
        "label_distribution": dict(distribution),
        "distractor_pages": distractors,
        "examples": examples,
    }
    path = save_json("fever_sample.json", payload)
    with_pages = sum(1 for e in examples if e["evidence_pages"])
    print(f"Wrote {len(examples)} examples to {path}")
    print("Label distribution:", dict(distribution))
    print(f"Examples with >=1 evidence page: {with_pages}; gold pages: {len(gold_pages)}; "
          f"distractors: {len(distractors)}; corpus: {len(gold_pages) + len(distractors)} pages")


if __name__ == "__main__":
    main()
