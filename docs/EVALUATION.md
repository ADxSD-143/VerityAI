# Evaluation

This document defines the evaluation protocol and records the **actual** measured results.
Results are produced only by the scripts in [`experiments/`](../experiments/README.md); nothing
here is estimated or hand-written.

## Benchmark

- **Dataset**: FEVER `v1.0`, official **development** split (`validation`).
- **Sample**: deterministic **stratified** sample of **500** claims, **seed 42**, proportional to
  the label distribution. The selected `dataset_index` / `fever_id` values are stored in
  `experiments/results/fever_sample.json`.
- **No tuning on the sample**: aggregation thresholds are principled defaults; the end-to-end
  check uses a separate small hand-labelled set.

### Corpus (documented deviation)

The full FEVER Wikipedia dump is several GB, so the retrieval corpus is **reconstructed from live
Wikipedia** for the union of gold evidence page titles in the sample (cached under
`data/fever_corpus/`). Consequences: relevance is **page-level**, and the text is current
Wikipedia rather than the frozen dump. This makes the retrieval numbers indicative rather than
directly comparable to sentence-level FEVER retrieval papers.

## Retrieval comparison

Same claims, same corpus, same preprocessing. Systems compared: TF-IDF (baseline), BM25, BGE
dense, hybrid BM25+BGE (RRF k=60), hybrid + cross-encoder rerank.

Metrics: **Recall@5**, **Precision@5**, **MRR**, **evidence coverage**, **mean latency**.
Definitions: [`docs/theory/retrieval-metrics.md`](theory/retrieval-metrics.md). Claims with no
gold page present in the corpus are excluded and counted separately (never scored as a miss).

Command:

```bash
python experiments/eval_retrieval.py --limit 500 --max-pages 1500
```

<!-- RETRIEVAL_RESULTS_START -->
### Recorded results (2026-10-10)

Corpus: **1161** Wikipedia pages (367 gold evidence pages for the sample + 800 deterministic
distractor pages); 6 titles unavailable. Claims evaluated: **330** — the 167 `NOT ENOUGH INFO`
claims have no evidence pages, and 3 claims had no gold page present in the corpus
(`skipped_no_gold_in_corpus = 170`).

| Retriever | Recall@5 | Precision@5 | MRR | mean latency |
|---|---|---|---|---|
| TF-IDF (baseline) | 0.958 | 0.221 | 0.941 | 6 ms |
| BM25 (lexical) | 0.943 | 0.221 | 0.901 | 7 ms |
| BGE dense | **0.973** | 0.226 | **0.985** | 28 ms |
| Hybrid (BM25 + BGE, RRF k=60) | 0.953 | 0.222 | 0.960 | 1 ms\* |
| Hybrid + cross-encoder rerank | 0.971 | 0.228 | 0.982 | 1528 ms |

\* the measured hybrid latency is the fusion step only; the BM25 and dense component latency is
reported on their own rows.

**Observations (recorded, not tuned):**

- All retrievers are close on this benchmark. Top-5 out of 1161 pages is a relatively easy task,
  and most claims have only 1–2 gold pages, so Precision@5 is bounded near 0.2.
- BGE dense measured the **highest MRR (0.985)**. Hybrid RRF measured slightly lower (0.960)
  because equal-weight RRF dilutes the stronger dense ranker with the weaker BM25 one.
- Hybrid + rerank recovers to 0.982 MRR but costs ~1.5 s per claim. **Conclusion: the reranker
  is left disabled by default** — the ranking gain is within noise, and the latency cost is large.
- The default runtime configuration (hybrid BM25 + BGE, no reranker) is retained for exact-term
  robustness (names, dates, numbers) in the *live* setting, which a page-level FEVER
  reconstruction does not measure. This is a documented judgement call, **not** a measured
  advantage over dense-only.

Raw results: `experiments/results/eval_retrieval.json`.
<!-- RETRIEVAL_RESULTS_END -->

## NLI comparison

Same fixed examples for each model. Construction: SUPPORTS/REFUTES premises are the
BM25-selected sentence from the claim's gold pages; `NOT ENOUGH INFO` premises are random non-gold
sentences. Expected mapping: SUPPORTS→entailment, REFUTES→contradiction, NEI→neutral.

Metrics: **accuracy**, **macro-F1**, **per-class precision/recall/F1**, **confusion matrix**,
**mean latency** (`docs/theory/classification-metrics.md`).

Commands:

```bash
python experiments/eval_nli.py --limit 500 --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
python experiments/eval_nli.py --limit 500 --model cross-encoder/nli-deberta-v3-small
```

<!-- NLI_RESULTS_START -->
### Recorded results (2026-10-10)

Label map read from the loaded model config (asserted by `test_nli_labels.py`):
`{0: 'entailment', 1: 'neutral', 2: 'contradiction'}`. 493 of the 500 claims yielded a premise
(7 had no usable premise).

**`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`** — accuracy **0.675**, macro-F1 **0.671**,
mean latency **90.5 ms** /pair.

| Class | Precision | Recall | F1 | n |
|---|---|---|---|---|
| entailment | 0.907 | 0.476 | 0.624 | 164 |
| neutral | 0.548 | 0.922 | 0.688 | 167 |
| contradiction | 0.802 | 0.623 | 0.701 | 162 |

Confusion matrix (rows = true, cols = predicted; order entailment, neutral, contradiction):

```
[[ 78  73  13]
 [  1 154  12]
 [  7  54 101]]
```

**Interpretation (recorded, not tuned).** The model is precise when it predicts entailment
(P = 0.907) but conservative (R = 0.476); most entailment errors become *neutral*. This is
expected under this construction: the premise is a **BM25-selected sentence from a reconstructed
page**, not the frozen FEVER gold sentence, so for many claims the retrieved sentence genuinely
does not entail the claim and *neutral* is the correct behaviour. These numbers indicate NLI
quality under our construction — they are not a FEVER leaderboard score.

**`cross-encoder/nli-deberta-v3-small`** — accuracy **0.448**, macro-F1 **0.458**,
mean latency **98.0 ms** /pair. Its label order is `{0: 'contradiction', 1: 'entailment',
2: 'neutral'}` — **different** from the base model, which is exactly why the runtime reads the
map from the loaded config and validates it (`test_nli_labels.py`). Assuming the order would have
corrupted every label.

| Class | Precision | Recall | F1 | n |
|---|---|---|---|---|
| entailment | 0.920 | 0.421 | 0.577 | 164 |
| neutral | 0.290 | 0.305 | 0.297 | 167 |
| contradiction | 0.417 | 0.623 | 0.500 | 162 |

**Decision.** The base model is retained as the default: it measured far higher accuracy
(0.675 vs 0.448) and macro-F1 (0.671 vs 0.458) at essentially the same CPU latency on this host.
`nli-deberta-v3-small` is documented as a smaller fallback for a host that cannot fit the base
model — **not** as an equivalent alternative.

Raw results: `experiments/results/eval_nli.json` (base) and
`experiments/results/eval_nli_small.json` (small).
<!-- NLI_RESULTS_END -->

## End-to-end

A small hand-labelled set of live claims, run through the real pipeline
(`experiments/eval_e2e.py`). The set is deliberately small and human-reviewed; treat it as
indicative only.

<!-- E2E_RESULTS_START -->
### Recorded results (2026-10-10)

8 hand-labelled live claims; **4/8** matched the expected status. Latency 2.0–19.8 s per claim
(live retrieval + NLI, warm models).

| Claim | Expected | Actual | Supporting passages |
|---|---|---|---|
| The Eiffel Tower is located in Paris. | SUPPORTED | CONFLICTING_EVIDENCE | 5 |
| The Great Wall of China is located in Japan. | REFUTED | REFUTED ✓ | 0 |
| The capital of Australia is Canberra. | SUPPORTED | SUPPORTED ✓ | 3 |
| The capital of Australia is Sydney. | REFUTED | CONFLICTING_EVIDENCE | 2 |
| Python was created by Guido van Rossum. | SUPPORTED | SUPPORTED ✓ | 4 |
| Mount Everest is the highest mountain above sea level on Earth. | SUPPORTED | SUPPORTED ✓ | 4 |
| The Amazon River is the longest river in the world by every measure. | CONFLICTING_EVIDENCE | REFUTED | 0 |
| Zorbax-9 was the first spacecraft to land on the Sun. | INSUFFICIENT_EVIDENCE | SUPPORTED | 1 |

**Interpretation (honest, not spun).**

- Two misses are **retrieval** artefacts: for "Eiffel Tower … Paris" and "capital of Australia is
  Sydney" the retriever also pulled a *different entity* (Eiffel Tower (Paris, Texas); pages about
  Sydney) whose passages the NLI model judged contradictory, so the pipeline reported
  `CONFLICTING_EVIDENCE` instead of a single verdict. The behaviour is traceable (the conflicting
  passage is returned), but it is a real precision problem.
- One miss is a **labelling judgement**: "The Amazon River is the longest river …" was labelled
  CONFLICTING; the pipeline returned REFUTED.
- **The important failure**: the nonsense claim "Zorbax-9 was the first spacecraft to land on the
  Sun" was reported **SUPPORTED** from a single passage (NLI entailment ≥ 0.50). The pipeline *did*
  set `limited_corroboration = true` and its explanation states the verdict rests on one
  independent source, but it still returned `SUPPORTED` rather than `INSUFFICIENT_EVIDENCE`. This
  is a genuine false-positive mode: one spurious entailment can carry a verdict.

**Decision recorded.** The aggregation policy was **not** tuned on this 8-claim set — doing so
would be fitting to the test. The false-positive mode is documented as a limitation, and
`limited_corroboration` is the current mitigation. A future improvement (not implemented here)
would require a higher NLI threshold, or ≥2 independent sources, before an unqualified `SUPPORTED`.

Raw: `experiments/results/eval_e2e.json`.
<!-- E2E_RESULTS_END -->

## Model and hardware details

<!-- RESOURCES_START -->
### Recorded measurements (2026-10-10, CPU-only)

Host: Intel i7-12650HX (14 cores / 20 threads), 15.73 GB RAM, Windows; `verity_device=cpu`.

| Model | Role | On-disk size | Cold load | Inference |
|---|---|---|---|---|
| `BAAI/bge-small-en-v1.5` | dense retrieval | 134.5 MB | 13.3 s | 58 ms/doc (batch of 8) |
| `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | NLI | 380.0 MB | 3.3 s | 103 ms/pair (batch of 4) |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | reranker | 91.8 MB | 3.3 s | 16 ms/pair (batch of 8) |

All three are below the ~500 MB per-artifact budget. An end-to-end analysis on live sources
measured **11.6 s** for one claim with warm models (live retrieval + hybrid ranking + NLI over the
top candidates).

Raw: `experiments/results/measure_resources.json`.
<!-- RESOURCES_END -->

## Language support

English-first. `BAAI/bge-small-en-v1.5` and the FEVER benchmark are English. Hindi/Hinglish input
is accepted by the UI but is **experimental / not verified**. A verified claim of multilingual
support would require a labelled multilingual evaluation set, which was not obtained.

## Reproducibility

Every result file records the dataset version, example ids, seed, model ids, thresholds, device
and the command used. Re-run the scripts to regenerate them. Results are kept distinct from
tuning decisions; if the sample is reused for further development, this document will note that
it is no longer an untouched test set.
