# Development log

Newest first. Records decisions, real errors and their root causes, and lessons learned.

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
