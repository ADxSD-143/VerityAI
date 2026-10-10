"""Page-level retrieval comparison on the fixed FEVER sample.

Compares four retrievers over one shared corpus:
    1. TF-IDF (evaluation baseline only)
    2. BM25 (lexical)
    3. BGE dense (semantic)
    4. Hybrid BM25 + BGE via RRF
    5. Hybrid + cross-encoder reranking

Corpus note (documented limitation): the full FEVER Wikipedia dump is several GB,
so the corpus is *reconstructed* from live Wikipedia for the union of gold evidence
page titles in the sample. Relevance is therefore page-level and the page text is
current Wikipedia, not the frozen FEVER dump.

Usage:
    python experiments/eval_retrieval.py --limit 500 --max-pages 1500
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import numpy as np  # noqa: E402
from _common import (  # noqa: E402
    fetch_many,
    load_json,
    mean,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    save_json,
)
from app.models_io import get_sentence_transformer  # noqa: E402
from app.retrieval.dense import DenseIndex  # noqa: E402
from app.retrieval.fusion import rrf_fuse  # noqa: E402
from app.retrieval.lexical import BM25Index  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402

TOP_K = 5
RERANK_POOL = 20


def build_corpus(examples, distractors, max_pages):
    titles: list[str] = []
    for example in examples:
        for title in example["evidence_pages"]:
            if title not in titles:
                titles.append(title)
    for title in distractors:
        if title not in titles:
            titles.append(title)
    return fetch_many(titles[:max_pages])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--max-pages", type=int, default=1500)
    parser.add_argument("--dense-model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--reranker-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    args = parser.parse_args()

    sample = load_json("fever_sample.json")
    examples = sample["examples"][: args.limit]
    distractors = sample.get("distractor_pages", [])
    print(f"Building corpus from {len(examples)} claims + {len(distractors)} distractors...")
    pages, missing = build_corpus(examples, distractors, args.max_pages)
    titles = list(pages.keys())
    texts = [pages[t] for t in titles]
    title_to_idx = {title: i for i, title in enumerate(titles)}
    print(f"Corpus: {len(titles)} pages ({len(missing)} unavailable)", flush=True)

    if not titles:
        raise SystemExit("Empty corpus - network unavailable? Nothing to evaluate.")

    print("Fitting retrievers...", flush=True)
    bm25 = BM25Index(texts)
    tfidf = TfidfVectorizer().fit(texts)
    tfidf_matrix = tfidf.transform(texts)
    model = get_sentence_transformer(args.dense_model)
    dense = DenseIndex(texts, model, args.dense_model)
    reranker = None
    try:
        from app.retrieval.rerank import CrossEncoderReranker

        reranker = CrossEncoderReranker(args.reranker_model)
    except Exception as exc:  # noqa: BLE001
        print(f"Reranker unavailable, skipping: {exc}")

    method_names = ("tfidf", "bm25", "bge", "hybrid", "hybrid_rerank")
    metrics = {
        name: {"recall": [], "precision": [], "mrr": [], "latency_ms": []}
        for name in method_names
    }
    paired_mrr_delta_bge_minus_hybrid: list[float] = []
    evaluated = 0
    skipped_no_gold = 0

    for example in examples:
        gold = set(example["evidence_pages"]) & set(titles)
        if not gold:
            skipped_no_gold += 1
            continue
        claim = example["claim"]
        evaluated += 1

        start = time.perf_counter()
        tfidf_sims = (tfidf_matrix @ tfidf.transform([claim]).T).toarray().ravel()
        tfidf_order = [titles[i] for i in np.argsort(-tfidf_sims)]
        metrics["tfidf"]["latency_ms"].append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        bm25_order = [titles[i] for i, _ in bm25.rank(claim, len(titles))]
        metrics["bm25"]["latency_ms"].append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        dense_order = [titles[i] for i, _ in dense.rank(claim, len(titles))]
        metrics["bge"]["latency_ms"].append((time.perf_counter() - start) * 1000)

        b_idx = [title_to_idx[t] for t in bm25_order]
        d_idx = [title_to_idx[t] for t in dense_order]
        start = time.perf_counter()
        fused_idx = [i for i, _ in rrf_fuse([b_idx, d_idx], k=60)]
        hybrid_order = [titles[i] for i in fused_idx]
        metrics["hybrid"]["latency_ms"].append((time.perf_counter() - start) * 1000)

        hybrid_rerank_order = None
        if reranker is not None:
            start = time.perf_counter()
            pool = fused_idx[:RERANK_POOL]
            reranked = reranker.rerank(claim, [texts[i] for i in pool], len(pool))
            hybrid_rerank_order = [titles[pool[loc]] for loc, _ in reranked] + [
                titles[i] for i in fused_idx[RERANK_POOL:]
            ]
            metrics["hybrid_rerank"]["latency_ms"].append((time.perf_counter() - start) * 1000)

        per_method = {"tfidf": tfidf_order, "bm25": bm25_order, "bge": dense_order,
                      "hybrid": hybrid_order}
        if hybrid_rerank_order is not None:
            per_method["hybrid_rerank"] = hybrid_rerank_order
        per_claim = {}
        for name, order in per_method.items():
            per_claim[name] = {
                "recall": recall_at_k(gold, order, TOP_K),
                "precision": precision_at_k(gold, order, TOP_K),
                "mrr": reciprocal_rank(gold, order),
            }
            for metric_name, value in per_claim[name].items():
                if value is not None:
                    metrics[name][metric_name].append(value)
        paired_mrr_delta_bge_minus_hybrid.append(
            per_claim["bge"]["mrr"] - per_claim["hybrid"]["mrr"]
        )

    summary = {}
    for name, values in metrics.items():
        if not values["recall"]:
            continue
        summary[name] = {
            "recall@5": mean(values["recall"]),
            "recall@5_ci95": bootstrap_mean_ci(values["recall"], seed=42),
            "precision@5": mean(values["precision"]),
            "precision@5_ci95": bootstrap_mean_ci(values["precision"], seed=43),
            "mrr": mean(values["mrr"]),
            "mrr_ci95": bootstrap_mean_ci(values["mrr"], seed=44),
            "mean_latency_ms": mean(values["latency_ms"]),
            "mean_latency_ms_ci95": bootstrap_mean_ci(values["latency_ms"], seed=45),
            "n": len(values["recall"]),
        }

    payload = {
        "benchmark": "fever-dev-page-retrieval",
        "sample_size": sample["selected"],
        "evaluated": evaluated,
        "skipped_no_gold_in_corpus": skipped_no_gold,
        "corpus_pages": len(titles),
        "corpus_pages_unavailable": len(missing),
        "top_k": TOP_K,
        "dense_model": args.dense_model,
        "reranker_model": args.reranker_model,
        "results": summary,
        "paired_comparison": {
            "metric": "MRR",
            "difference": "BGE dense minus hybrid RRF",
            "mean_difference": mean(paired_mrr_delta_bge_minus_hybrid),
            "difference_ci95": bootstrap_mean_ci(paired_mrr_delta_bge_minus_hybrid, seed=46),
            "n": len(paired_mrr_delta_bge_minus_hybrid),
        },
        "bootstrap": {
            "method": "non-parametric percentile bootstrap over claims",
            "resamples": 2000,
            "seed": 42,
            "confidence_level": 0.95,
        },
        "limitations": [
            "Corpus reconstructed from live Wikipedia, not the frozen FEVER dump.",
            "Relevance is page-level (gold evidence page in top-k), not sentence-level.",
        ],
    }
    path = save_json("eval_retrieval.json", payload)
    print(f"\nWrote {path}")
    for name, values in summary.items():
        print(f"  {name:14s} R@5={values['recall@5']:.3f} P@5={values['precision@5']:.3f} "
              f"MRR={values['mrr']:.3f} n={values['n']}")


if __name__ == "__main__":
    main()
