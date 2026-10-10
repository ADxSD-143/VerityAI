# Experiments

Reproducible evaluation scripts for VerityAI. Every script writes machine-readable
results to `experiments/results/`. Nothing here fabricates labels or metrics; when a
network fetch fails the failure is recorded.

Run from the repository root, in order:

```bash
python experiments/build_fever_sample.py --limit 500 --seed 42
python experiments/eval_retrieval.py   --limit 500 --max-pages 1500
python experiments/eval_nli.py         --limit 500 --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
python experiments/eval_nli.py         --limit 500 --model cross-encoder/nli-deberta-v3-small
python experiments/eval_e2e.py
python experiments/measure_resources.py
```

| Script | What it does | Output |
|---|---|---|
| `build_fever_sample.py` | Deterministic stratified FEVER dev sample (seed 42) | `results/fever_sample.json` |
| `eval_retrieval.py` | TF-IDF / BM25 / BGE / hybrid RRF / hybrid+rerank, page-level | `results/eval_retrieval.json` |
| `eval_nli.py` | Three-class NLI (entailment / neutral / contradiction) | `results/eval_nli.json` |
| `eval_e2e.py` | Live end-to-end pipeline on a small hand-labelled set | `results/eval_e2e.json` |
| `measure_resources.py` | Model sizes, cold-load times, inference latency | `results/measure_resources.json` |

## Documented limitations

- The FEVER Wikipedia dump is multi-GB, so the retrieval corpus is **reconstructed
  from live Wikipedia** for the gold evidence page titles in the sample. Relevance is
  page-level and the text is current Wikipedia, not the frozen FEVER dump.
- The NLI premise is a BM25-selected sentence from a reconstructed page, not the
  frozen FEVER gold sentence; `NOT ENOUGH INFO` premises are random non-gold sentences.
- `eval_e2e.py` uses a small hand-labelled set; treat the numbers as indicative.
- FEVER-retrieval performance does **not** imply real-world accuracy for current events,
  arbitrary websites, or other languages.

See `docs/EVALUATION.md` for the full protocol and the actual recorded results.
