# Development log

Newest first. Records decisions, real errors and their root causes, and lessons learned.

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
