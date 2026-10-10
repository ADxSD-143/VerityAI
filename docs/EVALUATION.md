# Evaluation

This document records measured results and the protocol used to regenerate them. Metrics must come
from scripts and saved artefacts, not estimates.

## Benchmark and contamination

- Dataset: FEVER v1.0 official development split, stratified sample of 500 claims, fixed seed 42.
- The sample has already been used for model/retriever selection; it is not an untouched held-out test set.
- Contamination risk: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli was trained/fine-tuned using FEVER (per model identity/documentation). FEVER-dev scores can be inflated by benchmark contamination and are not an independent estimate of real-world accuracy.
- FEVER is English. These results do not establish Hindi/Hinglish performance.

## Retrieval

The full FEVER Wikipedia dump is several GB, so the corpus is reconstructed from live Wikipedia and
scores page-level relevance, not frozen sentence-level evidence. The previous run used 1161 pages
(367 gold pages plus 800 distractors), evaluated 330 claims, and omitted claims without a gold page
in the reconstructed corpus. That corpus does not satisfy the harder-corpus requirement.

Run on a machine with network access and the model cache available:

    python experiments/build_fever_sample.py --limit 500 --seed 42 --distractors 4000
    python experiments/eval_retrieval.py --limit 500 --max-pages 5000

The retrieval script records percentile bootstrap 95% CIs for Recall@5, Precision@5, MRR and mean
latency, plus a paired per-claim bootstrap CI for the MRR difference (BGE dense minus hybrid RRF).
Resampling uses fixed seeds and 2,000 resamples. The prior point estimates are historical only;
the harder-corpus run is still pending. Choose the default retriever only after inspecting the
paired CI; do not claim a difference if the interval includes zero.

## NLI

Run both candidates on the same fixed sample:

    python experiments/eval_nli.py --limit 500 --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
    python experiments/eval_nli.py --limit 500 --model cross-encoder/nli-deberta-v3-small --out eval_nli_small.json

Recorded config label maps differ:
- Base: 0=entailment, 1=neutral, 2=contradiction.
- Small: 0=contradiction, 1=entailment, 2=neutral.

Runtime reads config.id2label; regression tests now cover both recorded candidate mappings. The
small model's saved confusion matrix is indexed in canonical order [entailment, neutral, contradiction]
and is consistent with the saved predictions, so the 0.448 accuracy is not explained by an obvious
label-order swap. The existing aggregate result cannot isolate the cause. Premise construction is
noisy: support/refute uses a BM25-selected sentence from reconstructed gold pages, while NEI uses a
random sentence from a pooled set. This limitation affects the evaluation and must not be described
as a pure model comparison.

The NLI script now saves deterministic percentile bootstrap 95% CIs for accuracy, macro-F1 and mean
CPU latency, with 2,000 resamples, and per-example latency. Prior point estimates from 2026-10-10:
base accuracy 0.675 / macro-F1 0.671 / mean latency 90.5 ms per pair; small accuracy 0.448 /
macro-F1 0.458 / mean latency 98.0 ms per pair. These prior values do not include the new CIs;
rerun both commands before using them as Phase 0 results.

## End-to-end held-out evaluation

The existing 8-claim live run is a historical diagnostic (4/8 matched) and has already been used to
identify a failure case. It is not a held-out estimate. The full set has not been rerun after the
single-source safeguard.

Phase 0 requires at least 60 human-labelled held-out claims stratified across verdict outcomes,
including opinions and allegations. The blank template is data/annotations/phase0_e2e_template.csv.
Human reviewers must fill labels and source URLs; ambiguous cases must be adjudicated. Do not
fabricate labels or auto-label using VerityAI. Keep a fixed seed/split; any failure case used to
change a policy moves to the tuning set.

For each model change, report CPU latency per claim and peak RAM. Bootstrap 95% CIs are required.
If a claimed improvement's interval includes zero, report it as inconclusive. Record negative results.
Do not tune tau_single on the existing 8-claim diagnostic or held-out set; choose it using a distinct
tuning split and report the precision-vs-insufficient-evidence curve.

## Existing point estimates (historical)

Retrieval, 330 evaluable claims / 1161-page corpus:

| Retriever | Recall@5 | Precision@5 | MRR | Mean latency |
|---|---:|---:|---:|---:|
| TF-IDF | 0.958 | 0.221 | 0.941 | 6 ms |
| BM25 | 0.943 | 0.221 | 0.901 | 7 ms |
| BGE dense | 0.973 | 0.226 | 0.985 | 28 ms |
| Hybrid RRF | 0.953 | 0.222 | 0.960 | fusion-only 1 ms |
| Hybrid + reranker | 0.971 | 0.228 | 0.982 | 1528 ms |

Historical end-to-end run: 4/8 statuses matched, 2–19.8 seconds per claim. The Zorbax-9 false
positive was re-checked once after the single-source safeguard and returned INSUFFICIENT_EVIDENCE
at entailment score 0.519 < tau_single=0.75. This is one observation, not an accuracy improvement estimate.

## Resource measurements

Prior CPU-only host: Intel i7-12650HX, 15.73 GB RAM. Recorded model sizes: BGE 134.5 MB,
DeBERTa base 380 MB, reranker 91.8 MB. Prior NLI latency was 90.5 ms/pair (base) and 98.0 ms/pair
(small). These are historical point measurements; rerun to obtain bootstrap intervals and current
peak RAM alongside any new model comparison.
