# Datasets

## FEVER (evaluation benchmark)

- **Name / version**: FEVER — Fact Extraction and VERification, `v1.0`, hosted as the
  Hugging Face `fever` dataset (config `v1.0`).
- **Split used**: official **development** split (`validation`).
- **License**: CC BY-SA 3.0 (as distributed with the FEVER dataset). The FEVER paper is
  Thorne et al., 2018 ("FEVER: a Large-scale Dataset for Fact Extraction and VERification").
- **Schema** (fields we use): `id`, `label` ∈ {`SUPPORTS`, `REFUTES`, `NOT ENOUGH INFO`},
  `claim`, `evidence` (page/sentence annotations for supported/refuted claims).
- **Sampling**: deterministic stratified sample of **500** claims, **seed 42**, proportional to
  the label distribution. The exact `dataset_index` and `fever_id` of every selected example are
  written to `experiments/results/fever_sample.json`.
- **Download / preparation**: `python experiments/build_fever_sample.py --limit 500 --seed 42`
  (requires the `eval` extra, which installs `datasets`).

### Corpus for retrieval evaluation

The full FEVER Wikipedia dump (`wiki_pages`, ~5.4M pages, multi-GB) is deliberately **not**
downloaded. Instead the retrieval corpus is **reconstructed from live Wikipedia** for the union
of gold evidence page titles in the sample, and cached under `data/fever_corpus/`.

Distractors are drawn deterministically (seed 42) from the evidence-page titles of **non-sampled**
claims. That deterministic pool is only **2525** titles, so the harder-corpus request
(`--distractors 5000`) is capped by the pool: the recorded harder run used 367 gold + 2042 usable
distractor pages = **2409 usable pages** (483 titles unavailable).

**Consequences (documented, not hidden):**

- Relevance is **page-level** (was a gold page retrieved in the top-k), not sentence-level.
- The page text is **current Wikipedia**, not the frozen FEVER dump, so it may differ from what
  the annotations were written against.
- FEVER-retrieval numbers therefore do **not** transfer directly to live-web retrieval.

## Live sources (application, not benchmark)

| Source | Type | Auth | Notes |
|---|---|---|---|
| Wikipedia / MediaWiki API | original evidence | none | descriptive User-Agent required |
| Wikidata | original structured facts | none | Action API + `Special:EntityData` |
| OpenAlex | original scholarly metadata | none | polite pool via `mailto` |
| Google Fact Check Tools (ClaimReview) | publisher verdict | free API key | disabled unless `FACTCHECK_API_KEY` is set |

## Data leakage and tuning

- No model is trained or fine-tuned on the evaluation examples.
- Aggregation thresholds are principled defaults, **not** tuned on the 500-claim sample;
  `experiments/eval_e2e.py` uses a separate small hand-labelled set.
- If the same sample is reused across many development decisions, it is no longer an untouched
  test set; that caveat is recorded in `docs/EVALUATION.md`.

## Class distribution

Actual counts for the selected sample are recorded in `experiments/results/fever_sample.json`
under `label_distribution` (read them from that file rather than from memory).
