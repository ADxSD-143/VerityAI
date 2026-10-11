# Development log

Newest first. Records decisions, real errors and their root causes, and lessons learned.

## 2026-10-10 — Annotation tooling; Latin-only tokenizer limitation

- Added `experiments/annotation_tools.py` (+ `backend/tests/test_annotation_tools.py`) to validate
  annotation CSVs and detect claim / near-duplicate leakage across the tuning/held-out split before
  any metric is computed. It never fills labels.
- **Found while testing**: `app.core.text.tokenize` uses `[A-Za-z0-9]+` (Latin-only), so non-Latin
  text (e.g. Devanagari) yields **zero** tokens; `shingles()` then falls back to a single `"<empty>"`
  gram, so *every* token-less text has Jaccard 1.0 with every other. This made three distinct Hindi
  claims look identical. Leakage detection now uses script-agnostic character n-grams.
- **Latent risk (not fixed here)**: the same collapse affects `analysis/independence.cluster_passages`
  for short (<5 Latin-token) and non-Latin passages — distinct passages can be merged into one
  "independent" source, which would overstate corroboration. Relevant to Phase 3 (Hindi/Hinglish).
  Recorded in `docs/READINESS.md`; not changed in this cycle to avoid altering clustering behaviour
  without measured justification.

## 2026-10-10 — NLI re-evaluation: base CI recorded, small model blocked

- Re-ran the NLI evaluation on the current code. Base model `DeBERTa-v3-base-mnli-fever-anli`:
  accuracy **0.675** [0.633, 0.716], macro-F1 **0.671** [0.630, 0.712], mean latency
  **159.9 ms/pair** [155.6, 165.1] (2000-resample percentile bootstrap; `eval_nli.json`).
- **Blocker**: `cross-encoder/nli-deberta-v3-small` failed to load — its DeBERTa-v2 tokenizer imports
  `sentencepiece`, and the host's Windows Application Control policy blocks the `sentencepiece` DLL
  (`ImportError: DLL load failed ... blocked by an Application Control policy`). Same policy class
  that forced older sklearn/pandas/pyarrow pins. The small model cannot be evaluated on this host;
  the historical 0.448/0.458 point estimates are not reproducible here and now carry no CI.
- Latency rose vs the earlier 90.5 ms/pair because the host was under CPU contention during the run
  (several stray Python processes); it is contention-dependent, not a model regression.
- **Lesson**: an application-control policy is a real evaluation constraint — a candidate model is
  only usable if its tokenizer/deps are permitted on the target host.

## 2026-10-10 — Single-source aggregation safeguard (false-positive fix)

- **Problem**: `docs/experiments/004-end-to-end.md` recorded the nonsense claim "Zorbax-9 … land on
  the Sun." reported `SUPPORTED` from one passage. The cause is aggregation, not retrieval or NLI:
  a single entailment ≥ `tau` (0.5) carried a verdict with no minimum evidence mass.
- **Fix**: a verdict resting on a **single independent source** must clear a higher bar, `tau_single`
  (`VERITY_TAU_NLI_SINGLE_SOURCE`, default 0.75); below it the status is `INSUFFICIENT_EVIDENCE`.
  Corroborated verdicts keep `tau`. Not tuned on the 8-claim set.
- **Measured re-check (live, one observation)**: the claim now returns `INSUFFICIENT_EVIDENCE`; its
  lone supporting passage (Wikidata "Sun Microsystems: instance of — software company.") scored
  entailment **0.519** — above `tau`, below `tau_single`.
- **Mechanism**: DeBERTa NLI is not a fact-checker; it matched salient tokens ("Sun") to an
  unrelated entity, the classic single-spurious-entailment mode.
- **Trade-off**: a genuine claim supported by only one weak source is now downgraded to
  `INSUFFICIENT_EVIDENCE` (recall↓ / precision↑ for `SUPPORTED`). A confident spurious entailment
  (≥ `tau_single`) from a lone source still passes — documented, not eliminated.
- **Tests**: `test_aggregation_regression.py` reproduces the failure shape; `test_aggregation.py`
  covers weak single-source support/contradiction, a preserved conflict, and a confident
  single-source verdict; `test_analyzer.py` verifies the setting is threaded end-to-end.

## 2026-10-10 — M2/M3 evaluation: real errors and fixes

- **Windows Application Control blocked newest wheels.** `scikit-learn 1.9.1`,
  `pandas 3.0.6` and `pyarrow 26.0.0` failed with *"DLL load failed ... blocked by an
  Application Control policy"*. Because `transformers` imports sklearn when it is installed,
  this also broke `transformers` → `sentence-transformers`. **Root cause**: the policy blocks
  the newly released binaries, not these libraries in general. **Fix**: pin
  `scikit-learn==1.5.2`, `pandas==2.2.3`, `pyarrow==17.0.0` (older, allowed). All imports OK.
- **FEVER dataset schema.** The HF `fever` `v1.0` config has **no `validation` split**; the
  development split is `labelled_dev`, and it requires `trust_remote_code=True`. Its rows are
  **flattened** (one row per evidence annotation, so claim ids repeat) with scalar
  `evidence_wiki_url` / `evidence_sentence_id` columns and `-LRB-`/`-RRB-` encoded titles.
  **Fix**: group rows back into claims and decode titles. Result: 500 claims, 333 with gold
  evidence, 367 gold pages, plus 800 deterministic distractor pages → 1167-page corpus.
- **`py` launcher broken**; **PyPI CDN throttled** (~33 KB/s vs ~245 KB/s on a mirror) — the
  install was switched to a PyPI mirror.
- **Performance bug in `eval_retrieval.py`**: `tfidf.transform(texts)` was recomputed for every
  claim, and `titles.index(...)` (O(n)) was used inside the per-claim loop. **Fix**: build the
  TF-IDF matrix once and use a `title → index` dict.
- **Measured reality**: corpus embedding of ~1161 Wikipedia pages with `bge-small-en-v1.5` on
  this CPU costs several minutes of real compute (~7 cores busy); cross-encoder reranking of
  333 × 20 pairs is the other dominant cost. Numbers, not assumptions, drove the evaluation
  runtime.
- **Lesson**: verify the evaluation dataset schema and the host's application-control policy
  *before* building on them.

## 2026-10-10 — M0: environment audit and control files

- **Environment**: Windows, Python 3.11.7, pip 26.2.1 (in venv), Node v24.15.0, git 2.55.0,
  i7-12650HX (14c/20t), 15.7 GB RAM, RTX 4050 (unused; CPU default), D: has 213 GB free.
- **Findings that changed the plan**:
  - The `py` launcher is broken (points at a missing `C:\Program Files\Python314`) → use the
    `python` executable directly.
  - **`gh` CLI is not installed** and there is no GitHub CLI config → the `gh repo create`
    workflow is blocked until it is installed/authenticated.
  - **No Hugging Face token** is present (`HF_TOKEN` unset, no cached token) → automated Space
    deploy is blocked until the user authenticates.
  - PyPI throughput from this host is slow (~30–80 KB/s for the first wheels), so the initial
    dependency install (dominated by the ~200 MB CPU torch wheel) is slow but not blocked.
- **Decisions**: vanilla no-build frontend; Hugging Face Spaces (Docker) as the deploy target;
  CPU-only torch; deterministic regex sentence segmentation instead of spaCy (smaller install,
  fully deterministic, no model download); a `VERITY_PRELOAD_MODELS` switch so tests never
  download models.
- **Lessons**: verify the toolchain *before* depending on it — `gh` and HF auth assumptions were
  wrong, so those steps are prepared rather than assumed.

## 2026-10-10 — M1: application skeleton and real retrieval

- Built the FastAPI app, the source adapters (Wikipedia/Wikidata/OpenAlex/FactCheck), the
  retrieval/dense/fusion modules, NLI + aggregation, the SSRF-safe fetcher, and the frontend.
- Design choice: each adapter **fails soft** (`status="error"`) so one broken source never fails
  a request; combined with "all sources failed → `UNABLE_TO_ASSESS`" this preserves the
  no-fabrication rule.
- Design choice: NLI label order is read from `config.id2label` and validated; a model that
  cannot be resolved is a hard load error rather than a silent mis-mapping.
- Design choice: aggregation counts **independent source groups** (document key plus
  near-duplicate text merge) so syndicated copies cannot inflate corroboration.
