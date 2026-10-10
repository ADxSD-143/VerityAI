# Experiment 001 — retrieval comparison (BM25 vs BGE vs RRF vs rerank)

**Question.** Which retrieval configuration should be the default?

**Hypothesis.** Hybrid (BM25 + BGE via RRF) with cross-encoder reranking will beat both single
retrievers.

**Setup.** FEVER `v1.0` `labelled_dev`, seed-42 stratified sample of 500 claims; 330 claims had a
gold evidence page in the reconstructed corpus. Corpus: 1161 Wikipedia pages (367 gold + 800
deterministic distractors). Metrics: page-level Recall@5, Precision@5, MRR; mean latency.

**Baseline.** TF-IDF (scikit-learn) — evaluation baseline only, never used at runtime.

**Command.**

```bash
python experiments/build_fever_sample.py --limit 500 --seed 42 --distractors 800
python experiments/eval_retrieval.py --limit 500
```

**Results.**

| Retriever | Recall@5 | Precision@5 | MRR | mean latency |
|---|---|---|---|---|
| TF-IDF | 0.958 | 0.221 | 0.941 | 6 ms |
| BM25 | 0.943 | 0.221 | 0.901 | 7 ms |
| BGE dense | **0.973** | 0.226 | **0.985** | 28 ms |
| Hybrid (RRF k=60) | 0.953 | 0.222 | 0.960 | 1 ms |
| Hybrid + rerank | 0.971 | 0.228 | 0.982 | 1528 ms |

**Interpretation.** The hypothesis was **not** confirmed. BGE dense alone measured the highest MRR
(0.985). Equal-weight RRF slightly *hurt* MRR (0.960) by diluting the stronger dense ranker with the
weaker BM25 one. Reranking recovered to 0.982 but costs ~1.5 s/claim.

**Limitations.** Page-level relevance only; corpus reconstructed from live Wikipedia, not the frozen
FEVER dump; top-5-of-1161 is an easy task, and Precision@5 is bounded near 0.2 because most claims
have 1–2 gold pages. These numbers do not describe live-web retrieval.

**Decision (original run).** Keep the **hybrid** configuration as the runtime default for exact-term
robustness (names, dates, numbers) in the live setting — an explicit judgement call, **not** a
measured advantage. Keep the reranker **disabled by default** (`VERITY_USE_RERANKER=false`); it
remains available and evaluated. Recorded honestly rather than switching the default purely on this
page-level benchmark.

**Artefacts.** `experiments/results/eval_retrieval.json`.

## Follow-up — harder corpus (2026-10-10)

Re-run on a harder corpus. The deterministic distractor pool from non-sampled FEVER `labelled_dev`
evidence titles caps at **2525** titles, so `--distractors 5000` produced a **2409-page** usable
corpus (367 gold + 2042 distractors; 483 unavailable), 330 evaluable claims. Bootstrap 95% CIs.

| Retriever | Recall@5 [95% CI] | MRR [95% CI] |
|---|---|---|
| BGE dense | 0.968 [0.952, 0.981] | **0.975 [0.961, 0.987]** |
| Hybrid (RRF k=60) | 0.946 [0.923, 0.967] | 0.955 [0.935, 0.974] |
| Hybrid + rerank | 0.965 [0.948, 0.980] | 0.966 [0.948, 0.980] |
| TF-IDF | 0.938 [0.914, 0.959] | 0.901 [0.876, 0.925] |
| BM25 | 0.916 [0.887, 0.943] | 0.858 [0.826, 0.889] |

Paired per-claim MRR difference (BGE dense − hybrid RRF) = **+0.0196, 95% CI [0.0027, 0.0377]**
(n=330) — excludes zero.

**Decision (revised).** The runtime default is now **dense-only** (`VERITY_RETRIEVAL_MODE=dense`),
chosen from data; `hybrid` remains selectable. The exact-term-robustness rationale for hybrid is an
untested live-setting hypothesis, **not** a measured advantage, and no longer the default.

Reproduce: `python experiments/build_fever_sample.py --limit 500 --seed 42 --distractors 5000` then
`python experiments/eval_retrieval.py --limit 500 --max-pages 5000`.
