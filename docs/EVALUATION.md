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
_Results recorded after running the command above._
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
_Results recorded after running the commands above._
<!-- NLI_RESULTS_END -->

## End-to-end

A small hand-labelled set of live claims, run through the real pipeline
(`experiments/eval_e2e.py`). The set is deliberately small and human-reviewed; treat it as
indicative only.

<!-- E2E_RESULTS_START -->
_Results recorded after running `python experiments/eval_e2e.py`._
<!-- E2E_RESULTS_END -->

## Model and hardware details

<!-- RESOURCES_START -->
_Recorded by `python experiments/measure_resources.py`: model ids, revisions, on-disk sizes,
cold-load times and inference latency on the test machine._
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
