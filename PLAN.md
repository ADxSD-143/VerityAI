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

## M1 — Application skeleton and real evidence retrieval — `PASS`

**Objective.** End-to-end foundation with real, source-attributed retrieval (no ML yet).
**Deliverables.** FastAPI backend; responsive static frontend; input validation; MediaWiki
source adapter; structured response; source links; `/health`; unit + integration tests;
documented local startup.
**Verification.** `pytest -q` → 63 passed; `ruff check` → clean; server up; `GET /health` OK;
`POST /api/analyze` on "The Eiffel Tower is located in Paris." returned real Wikipedia +
Wikidata + OpenAlex passages with URLs and a traceable verdict (11.6 s, not degraded);
frontend + assets served; `POST /api/analyze-url` with a metadata IP → 400 `unsafe_url`;
empty body → 422.
**Gate.** **PASS** — app starts with documented commands; a claim returns real source-attributed
passages; no fabrication on failure (fact-check source reported as `skipped`); focused +
integration tests pass.
**Note.** A simple claim returned `CONFLICTING_EVIDENCE` because retrieval also pulled the
"Eiffel Tower (Paris, Texas)" article and one passage was judged contradictory. This is honest,
traceable behaviour (and a quality item to watch in M2/M3), not a gate failure.

## M2 — Pretrained semantic retrieval — `PASS`

**Objective.** Replace keyword-only retrieval with a hybrid semantic pipeline.
**Deliverables.** BGE dense retrieval (official query prefix, normalized embeddings);
BM25 lexical; RRF fusion + dedup; disk/in-process passage-embedding cache; TF-IDF/BM25
baselines for evaluation only; retrieval benchmark script; measured results.
**Verification.** `python experiments/eval_retrieval.py` over the FEVER sample.
**Gate.** BGE loads and runs; hybrid tested against both arms; ranking metrics reproducible
(Recall@5, Precision@5, MRR, coverage); model + corpus recorded; default config justified by
measured performance; no silent keyword-only fallback without a visible degraded mode.
**Recorded.** `experiments/eval_retrieval.py` over 330 evaluable claims / 1161-page reconstructed
corpus: TF-IDF R@5 0.958 / MRR 0.941; BM25 0.943 / 0.901; BGE dense 0.973 / 0.985; hybrid RRF
0.953 / 0.960; hybrid+rerank 0.971 / 0.982. Dense measured highest MRR; hybrid retained as default
for exact-term robustness (documented judgement call). Reranker left disabled by default.
**Risks/fallback.** BGE too slow/large → `bge-small` retained; document latency.

## M3 — NLI, aggregation, claim assessment — `PASS`

**Objective.** Add entailment-based assessment and conservative aggregation.
**Deliverables.** NLI integration with config-read label map + tests; source independence
clustering; conservative aggregation (SUPPORTED/REFUTED/INSUFFICIENT/CONFLICTING/
UNABLE_TO_ASSESS); optional reranker evaluation; classification benchmark.
**Verification.** `python experiments/eval_nli.py`; end-to-end `POST /api/analyze`.
**Gate.** NLI loads and emits valid outputs; label-map tests pass; relevance vs entailment
kept separate; conflict never auto-becomes a confident verdict; metrics reproducible; a full
end-to-end analysis completes.
**Recorded.** `experiments/eval_nli.py` (n=493): base model accuracy 0.675 / macro-F1 0.671
(label map `0=entailment,1=neutral,2=contradiction`); small model 0.448 / 0.458 (label map
`0=contradiction,1=entailment,2=neutral` — different order, read from config). Base retained as
default. Label-map tests pass; end-to-end analysis completes.
**Risks/fallback.** DeBERTa-base too heavy for the host → benchmark `nli-deberta-v3-small`,
switch default, document the trade-off.

## M4 — Data, evaluation, and multilingual assessment — `PASS`

**Objective.** Reproducible, honest evaluation on real data.
**Deliverables.** FEVER sample builder (500 @ seed 42); retrieval eval; NLI eval; end-to-end
eval on a small hand-labelled set; saved JSON/CSV results with full provenance; dataset docs;
multilingual assessment limited to a documented experimental note.
**Verification.** Re-run every `experiments/*.py`; results regenerate.
**Gate.** No fabricated labels; splits respected; example IDs preserved; metrics regenerable;
limitations documented.
**Recorded.** `experiments/results/` holds `fever_sample.json` (500 claims, seed 42, distribution
166/167/167, 367 gold + 800 distractor pages), `eval_retrieval.json`, `eval_nli.json`,
`eval_nli_small.json`, `eval_e2e.json`, `measure_resources.json`. Multilingual support is
documented as **experimental / unverified** (no labelled multilingual set obtained).
**Risks/fallback.** FEVER wiki dump too large → fixed recorded corpus reconstructed from
live Wikipedia for gold + distractor titles; limitation documented.

## M5 — Security and reliability — `PASS`

**Objective.** SSRF-safe URL extraction and robust failure handling.
**Deliverables.** URL validation (scheme, IP ranges, redirects); size/time caps; content-type
allowlist; timeout/error handling; security tests; dependency + secret review; regression suite.
**Verification.** `pytest -q -m "not live"` incl. `backend/tests/test_url_safety.py`.
**Gate.** Security-critical tests pass; failure paths never fabricate; no secrets committed;
app stays functional when external sources fail.
**Recorded.** `backend/tests/test_url_safety.py` (13 tests) covers private/loopback/link-local/
metadata IPv4, IPv6 and IPv4-mapped forms, unsupported schemes, embedded credentials, unusual
ports, missing host, **redirect re-validation to a private address**, oversized response,
unsupported content type, timeout and upstream error status. Full suite: **69 tests pass**, ruff
clean. Secret scan clean (no `.env`, no secret-named files, no tracked file > 1 MB). Failure paths
(source error, all-sources-failed → `UNABLE_TO_ASSESS`, unknown URL → 400) are covered by tests.
**Limitation recorded:** passing these tests does not prove comprehensive security, and DNS
rebinding TOCTOU is mitigated, not eliminated (`docs/SECURITY.md`).

## M6 — Documentation and CI — `PASS`

**Objective.** Complete, accurate documentation and continuous integration.
**Deliverables.** `README.md`, `docs/ARCHITECTURE.md`, `DATASETS.md`, `EVALUATION.md`,
`DEVELOPMENT_LOG.md`, `SECURITY.md`, `API.md`, `docs/theory/*`, `docs/experiments/*`,
`.github/workflows/ci.yml`.
**Verification.** CI runs `ruff check` + `pytest -q`; local clean-env setup works.
**Gate.** Setup works from clean env; CI runs documented checks; metrics traceable to code +
saved results; docs distinguish implemented/experimental/planned.
**Recorded.** Docs written: `README.md`, `docs/ARCHITECTURE.md`, `API.md`, `SECURITY.md`,
`DATASETS.md`, `EVALUATION.md` (with recorded results), `DEVELOPMENT_LOG.md`, 11 `docs/theory/*`
pages, 4 `docs/experiments/*` records. `.github/workflows/ci.yml` runs `ruff` + `pytest`.
**CI verified on GitHub:** run #2 on `f97a075` concluded **success** (run id `38047977416`); run #1
on `47a7602` also succeeded. Repo is public at `https://github.com/ADxSD-143/VerityAI`.
**Risks/fallback.** none blocking.

## M7 — GitHub publication and free deployment — `IN PROGRESS`

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
**Recorded (GitHub half — done).** Repository is **public** at
`https://github.com/ADxSD-143/VerityAI`; `main` = `eec56f7`; GitHub Actions CI **green**
(run `38050601549`, success).
**Pending (deployment half).** The Hugging Face Space is **not deployed**. No Hugging Face token is
present (no `HF_TOKEN`, no cached login) and Docker is not installed, so the image cannot be built
locally (HF Spaces builds it server-side). Deploy artifacts are ready (`Dockerfile`, README Spaces
frontmatter, port 7860). Required user action: `huggingface-cli login` (write token), create the
Docker Space, push, then verify the public frontend + `/health` + one real analysis and record the
URL in `README.md` (`DEPLOY_URL`). M7 is **not** `PASS` until that is verified.


---

## Product Phase 0 — reliability hardening (ACTIVE)

This product roadmap is separate from the original engineering milestones M0–M7 above.
Do not begin Phase 1 web-search expansion until this phase's gate passes.

Phase 0 work includes per-client request limits, body and analysis timeouts, NLI label-map
regression tests, bootstrap confidence intervals, a harder retrieval corpus, and a separate
human-labelled held-out set.

The annotation template is data/annotations/phase0_e2e_template.csv. Gold labels must be reviewed
by a human and must not be generated automatically. Existing FEVER results are not an untouched
held-out set, and the existing 8-claim end-to-end diagnostic must not be used to tune thresholds.

**Gate status: IN PROGRESS.** Tests and CI must pass; the larger-corpus retrieval evaluation and its
paired bootstrap interval must be recorded; both NLI candidates need fresh confidence intervals;
at least 60 human-labelled held-out claims must exist; the tau_single curve must use a separate
tuning split. Hugging Face deployment remains blocked until the owner provides credentials and
authorizes Space creation.
