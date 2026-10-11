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
scores page-level relevance, not frozen sentence-level evidence. The earlier run used 1161 pages
(367 gold pages plus 800 distractors); it is superseded by the harder 2409-page run recorded below.
Claims without a gold page in the reconstructed corpus are omitted and counted.

Run on a machine with network access and the model cache available:

    python experiments/build_fever_sample.py --limit 500 --seed 42 --distractors 5000
    python experiments/eval_retrieval.py --limit 500 --max-pages 5000

### Recorded harder-corpus run (2026-10-10)

The deterministic distractor pool from non-sampled FEVER `labelled_dev` evidence titles is **2525**
titles, so the `--distractors 5000` request is capped by the pool. Corpus: **2409 usable pages**
(367 gold + 2042 distractors; 483 titles unavailable), 330 evaluable claims. Percentile bootstrap
95% CIs, 2000 resamples, fixed seeds.

| Retriever | Recall@5 [95% CI] | Precision@5 [95% CI] | MRR [95% CI] |
|---|---|---|---|
| TF-IDF | 0.938 [0.914, 0.959] | 0.212 [0.205, 0.221] | 0.901 [0.876, 0.925] |
| BM25 | 0.916 [0.887, 0.943] | 0.212 [0.202, 0.223] | 0.858 [0.826, 0.889] |
| **BGE dense** | 0.968 [0.952, 0.981] | 0.222 [0.214, 0.232] | **0.975 [0.961, 0.987]** |
| Hybrid RRF | 0.946 [0.923, 0.967] | 0.219 [0.210, 0.229] | 0.955 [0.935, 0.974] |
| Hybrid + rerank | 0.965 [0.948, 0.980] | 0.224 [0.215, 0.235] | 0.966 [0.948, 0.980] |

Paired per-claim MRR difference (BGE dense − hybrid RRF) = **+0.0196, 95% CI [0.0027, 0.0377]**
(n=330). The interval excludes zero: on this reconstructed page-level task BGE dense is better than
hybrid and is also cheaper (dense-only ≈ 29.5 ms/claim vs BM25+dense+fusion ≈ 44 ms).

**Decision.** The runtime default is now **dense-only** (`VERITY_RETRIEVAL_MODE=dense`); `hybrid`
remains selectable. The earlier justification for hybrid — exact-term robustness for names, dates
and numbers in the *live* setting — is **not** measured by this page-level benchmark and is no longer
the default; treat it as an untested hypothesis. The reranker stays disabled by default. Negative
result recorded: the original hypothesis (hybrid + rerank beats single retrievers) was not confirmed.

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

### Recorded NLI results (2026-10-10, CPU-only)

Base model `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, n=493, percentile bootstrap 95% CIs
(2000 resamples, fixed seeds; `experiments/results/eval_nli.json`):

- accuracy **0.675** [0.633, 0.716]
- macro-F1 **0.671** [0.630, 0.712]
- mean latency **159.9 ms/pair** [155.6, 165.1] — this host was under CPU contention during the
  run, so it is not directly comparable to the earlier 90.5 ms point estimate.

**Small candidate could not be re-run on this host — BLOCKED (environment).**
`cross-encoder/nli-deberta-v3-small` is DeBERTa-v2, whose tokenizer imports `sentencepiece`; the
host's Windows Application Control policy blocks the `sentencepiece` native DLL
(`ImportError: DLL load failed while importing _sentencepiece ... blocked by an Application Control
policy`). The historical small-model point estimates (accuracy 0.448 / macro-F1 0.458) are therefore
**not reproducible on this host** and carry no CI. This is an environment blocker, not a model
result; do not cite 0.448/0.458 as current. Reproduce the base result on a host where models load:
`python experiments/eval_nli.py --limit 500 --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`.

## End-to-end held-out evaluation

The existing 8-claim live run is a historical diagnostic (4/8 matched) and has already been used to
identify a failure case. It is not a held-out estimate. The full set has not been rerun after the
single-source safeguard.

Phase 0 requires at least 60 human-labelled held-out claims stratified across verdict outcomes,
including opinions and allegations. The blank template is data/annotations/phase0_e2e_template.csv.
Human reviewers must fill labels and source URLs; ambiguous cases must be adjudicated. Do not
fabricate labels or auto-label using VerityAI. Keep a fixed seed/split; any failure case used to
change a policy moves to the tuning set.

Validate an annotation file before using it for any metric:

    python experiments/annotation_tools.py --path data/annotations/phase0_e2e_template.csv --schema gold

The validator (`experiments/annotation_tools.py`) enforces the column schema and claim-type/verdict
enums, flags duplicate case ids and claim texts, errors on near-duplicate claim leakage across the
tuning/held-out split (measured with script-agnostic character n-grams), and requires >=60 reviewed
held-out rows in gold mode. It never fills labels; unreviewed rows are excluded, never guessed.

Once at least 60 held-out rows are reviewed, score them end to end:

    python experiments/eval_e2e_heldout.py --path data/annotations/phase0_e2e_template.csv

The harness (`experiments/eval_e2e_heldout.py`) re-validates the file and **refuses to run** if it
fails (unreviewed or under-sized held-out set). It scores factual rows on the verdict and non-factual
rows on handling (opinions/predictions/allegations must not receive SUPPORTED/REFUTED), reports
overall and per-claim-type agreement with bootstrap 95% CIs, and writes
`experiments/results/eval_e2e_heldout.json`. It never turns model output into gold.

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
