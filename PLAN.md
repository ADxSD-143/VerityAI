# PLAN.md — VerityAI milestones

Status vocabulary: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `PASS`.
A milestone is `PASS` only after its acceptance gate is verified with real commands.

## Locked decisions

| Decision | Choice |
|---|---|
| Frontend | Vanilla HTML/CSS/JS, no build step, served as static files by FastAPI |
| Hosting | Hugging Face Spaces, Docker SDK, free CPU tier |
| Backend | FastAPI + Pydantic v2, Uvicorn |
| Dense retrieval | `BAAI/bge-small-en-v1.5` |
| Lexical retrieval | BM25 (`rank_bm25`), TF-IDF baseline for eval only |
| Fusion | Reciprocal Rank Fusion, k=60 |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (default only if eval justifies) |
| NLI | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`; small variant benchmarked |
| Benchmark | FEVER dev, deterministic stratified sample of 500, seed 42 |

---

## M0 — Audit and planning — `PASS`

**Objective.** Establish environment facts and executable plan.
**Deliverables.** Environment audit; repo structure; `AGENTS.md`; `PLAN.md`;
`docs/PROJECT_STATUS.md`; dependency + model candidates with verification plan.
**Verification.** `python --version`, `node --version`, `git --version`, `gh --version`,
hardware/disk/network probes recorded in `docs/PROJECT_STATUS.md`.
**Gate.** Plan is concrete/executable; compute + hosting constraints recorded; no mandatory
paid service; every proposed model has a verification plan.

## M1 — Application skeleton and real evidence retrieval — `IN PROGRESS`

**Objective.** End-to-end foundation with real, source-attributed retrieval (no ML yet).
**Deliverables.** FastAPI backend; responsive static frontend; input validation; MediaWiki
source adapter; structured response; source links; `/health`; unit + integration tests;
documented local startup.
**Verification.** `pytest -q`; start server; `GET /health`; `POST /api/analyze` on a real
claim returns real Wikipedia passages with URLs; simulate source failure → no fabrication.
**Gate.** App starts with documented commands; a claim returns real source-attributed
passages; no fabrication on failure; focused + integration tests pass.
**Risks/fallback.** Wikipedia API unavailable → adapter reports failure and the analysis
returns `UNABLE_TO_ASSESS`, never invented evidence.

## M2 — Pretrained semantic retrieval — `NOT STARTED`

**Objective.** Replace keyword-only retrieval with a hybrid semantic pipeline.
**Deliverables.** BGE dense retrieval (official query prefix, normalized embeddings);
BM25 lexical; RRF fusion + dedup; disk/in-process passage-embedding cache; TF-IDF/BM25
baselines for evaluation only; retrieval benchmark script; measured results.
**Verification.** `python experiments/eval_retrieval.py` over the FEVER sample.
**Gate.** BGE loads and runs; hybrid tested against both arms; ranking metrics reproducible
(Recall@5, Precision@5, MRR, coverage); model + corpus recorded; default config justified by
measured performance; no silent keyword-only fallback without a visible degraded mode.
**Risks/fallback.** BGE too slow/large → `bge-small` retained; document latency.

## M3 — NLI, aggregation, claim assessment — `NOT STARTED`

**Objective.** Add entailment-based assessment and conservative aggregation.
**Deliverables.** NLI integration with config-read label map + tests; source independence
clustering; conservative aggregation (SUPPORTED/REFUTED/INSUFFICIENT/CONFLICTING/
UNABLE_TO_ASSESS); optional reranker evaluation; classification benchmark.
**Verification.** `python experiments/eval_nli.py`; end-to-end `POST /api/analyze`.
**Gate.** NLI loads and emits valid outputs; label-map tests pass; relevance vs entailment
kept separate; conflict never auto-becomes a confident verdict; metrics reproducible; a full
end-to-end analysis completes.
**Risks/fallback.** DeBERTa-base too heavy for the host → benchmark `nli-deberta-v3-small`,
switch default, document the trade-off.

## M4 — Data, evaluation, and multilingual assessment — `NOT STARTED`

**Objective.** Reproducible, honest evaluation on real data.
**Deliverables.** FEVER sample builder (500 @ seed 42); retrieval eval; NLI eval; end-to-end
eval on a small hand-labelled set; saved JSON/CSV results with full provenance; dataset docs;
multilingual assessment limited to a documented experimental note.
**Verification.** Re-run every `experiments/*.py`; results regenerate.
**Gate.** No fabricated labels; splits respected; example IDs preserved; metrics regenerable;
limitations documented.
**Risks/fallback.** FEVER wiki dump too large → fixed recorded corpus reconstructed from
live Wikipedia for gold + distractor titles; limitation documented.

## M5 — Security and reliability — `NOT STARTED`

**Objective.** SSRF-safe URL extraction and robust failure handling.
**Deliverables.** URL validation (scheme, IP ranges, redirects); size/time caps; content-type
allowlist; timeout/error handling; security tests; dependency + secret review; regression suite.
**Verification.** `pytest -q -m "not live"` incl. `backend/tests/test_url_safety.py`.
**Gate.** Security-critical tests pass; failure paths never fabricate; no secrets committed;
app stays functional when external sources fail.

## M6 — Documentation and CI — `NOT STARTED`

**Objective.** Complete, accurate documentation and continuous integration.
**Deliverables.** `README.md`, `docs/ARCHITECTURE.md`, `DATASETS.md`, `EVALUATION.md`,
`DEVELOPMENT_LOG.md`, `SECURITY.md`, `API.md`, `docs/theory/*`, `docs/experiments/*`,
`.github/workflows/ci.yml`.
**Verification.** CI runs `ruff check` + `pytest -q`; local clean-env setup works.
**Gate.** Setup works from clean env; CI runs documented checks; metrics traceable to code +
saved results; docs distinguish implemented/experimental/planned.

## M7 — GitHub publication and free deployment — `NOT STARTED`

**Objective.** Publish source and deploy publicly.
**Deliverables.** Public `VerityAI` repo; pushed commits; verified CI; HF Space Docker
deploy; verified public URLs; end-to-end smoke test.
**Verification.** `gh repo view` / remote check; `git log` on remote; `GET <space>/health`;
public frontend load; one real analysis.
**Gate.** Correct owner + remote verified; expected commit exists remotely; CI checked;
public frontend + `/health` respond; ≥1 real end-to-end analysis succeeds (or exact external
blocker reported); no secrets exposed.
**Risks/fallback.** `gh` CLI missing / HF token missing → prepare all artifacts, document the
exact blocker and the one manual step required; never claim deployment without verification.
