"""Three-class NLI evaluation on the fixed FEVER sample.

Construction (documented):
  * SUPPORTS / REFUTES: premise = the sentence most similar (BM25) to the claim among
    the claim's gold evidence pages.
  * NOT ENOUGH INFO: premise = a sentence drawn from a non-gold page.
Expected mapping: SUPPORTS->entailment, REFUTES->contradiction, NEI->neutral.

Limitation: FEVER sentence-level annotations are approximated by a BM25-selected
sentence from a reconstructed page - this is not the frozen FEVER gold sentence.

Usage:
    python experiments/eval_nli.py --limit 500 --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from _common import LABEL_TO_NLI, fetch_many, load_json, save_json  # noqa: E402
from app.analysis.nli import CANONICAL_LABELS, NLIModel  # noqa: E402
from app.core.text import split_sentences, tokenize  # noqa: E402
from app.retrieval.lexical import BM25Index  # noqa: E402


def page_sentences(text: str) -> list[str]:
    return [s.text for s in split_sentences(text) if len(tokenize(s.text)) >= 5]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--model", default="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="eval_nli.json")
    args = parser.parse_args()

    sample = load_json("fever_sample.json")
    examples = sample["examples"][: args.limit]

    needed: list[str] = []
    for example in examples:
        for title in example["evidence_pages"]:
            if title not in needed:
                needed.append(title)
    page_map, _ = fetch_many(needed)
    pages: dict[str, str] = {title: page_map.get(title, "") for title in needed}

    distractor_pool: list[str] = []
    for text in pages.values():
        distractor_pool.extend(page_sentences(text))
    rng = random.Random(args.seed)

    nli = NLIModel(args.model)
    print(f"Loaded {args.model}; label map = {nli.label_map}")

    y_true: list[str] = []
    y_pred: list[str] = []
    latencies: list[float] = []
    records: list[dict] = []

    for example in examples:
        gold_texts = [pages[t] for t in example["evidence_pages"] if pages.get(t)]
        premise = None
        if example["label"] in ("SUPPORTS", "REFUTES") and gold_texts:
            pool: list[str] = []
            for text in gold_texts:
                pool.extend(page_sentences(text))
            if not pool:
                continue
            if len(pool) == 1:
                premise = pool[0]
            else:
                ranked = BM25Index(pool).rank(example["claim"], 1)
                if not ranked:
                    continue
                premise = pool[ranked[0][0]]
        elif example["label"] == "NOT ENOUGH INFO" and distractor_pool:
            premise = rng.choice(distractor_pool)

        if premise is None:
            continue

        start = time.perf_counter()
        scored = nli.predict(premise, example["claim"])
        latencies.append((time.perf_counter() - start) * 1000)

        y_true.append(LABEL_TO_NLI[example["label"]])
        y_pred.append(scored.label)
        records.append(
            {
                "claim": example["claim"],
                "fever_label": example["label"],
                "expected": LABEL_TO_NLI[example["label"]],
                "predicted": scored.label,
                "score": scored.score,
                "premise": premise[:400],
            }
        )

    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )

    labels = list(CANONICAL_LABELS)
    accuracy = accuracy_score(y_true, y_pred) if y_true else None
    macro_f1 = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0) if y_true else None
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0) if y_true else {}
    matrix = confusion_matrix(y_true, y_pred, labels=labels).tolist() if y_true else []

    payload = {
        "benchmark": "fever-dev-nli",
        "model": args.model,
        "label_map": {str(k): v for k, v in nli.label_map.items()},
        "n": len(y_true),
        "label_distribution": dict(Counter(y_true)),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": report,
        "confusion_matrix": {"labels": labels, "matrix": matrix},
        "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "records": records,
        "limitations": [
            "Premise is a BM25-selected sentence from a reconstructed page, not the frozen FEVER gold sentence.",
            "NOT ENOUGH INFO premises are random non-gold sentences.",
        ],
    }
    path = save_json(args.out, payload)
    print(f"\nWrote {path}")
    print(f"n={len(y_true)} accuracy={accuracy} macro_f1={macro_f1}")
    print("confusion matrix (rows=true, cols=pred):", labels, matrix)


if __name__ == "__main__":
    main()
