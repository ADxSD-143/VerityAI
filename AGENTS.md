# AGENTS.md — VerityAI engineering instructions

Operational guide for any agent or developer working in this repository.
Read this file first, then `PLAN.md`, then `docs/PROJECT_STATUS.md`.

## Mission

VerityAI checks claims against **retrieved evidence**. It does not "know" truth.
Every output must be traceable to a source passage, and uncertainty must be reported
honestly. Never fabricate evidence, citations, metrics, or success.

## Architecture (component boundaries)

```
input -> validation -> (URL extraction, SSRF-safe) -> claim extraction
      -> source adapters (Wikipedia/MediaWiki, Wikidata, OpenAlex, optional FactCheck)
      -> retrieval: BM25 (lexical) + BGE (dense) -> RRF fusion -> optional cross-encoder rerank
      -> NLI (premise = passage, hypothesis = claim)
      -> source independence clustering -> conservative aggregation -> report
```

- `backend/app/sources/` — one adapter per external source; each declares access method,
  auth, rate limits, failure behavior, and whether it returns original evidence or a
  publisher verdict. No adapter may invent a source or bypass access controls.
- `backend/app/retrieval/` — lexical, dense, fusion, rerank. TF-IDF is eval/fallback only.
- `backend/app/analysis/` — NLI, independence, aggregation. NLI label order is read from
  the loaded model config, never assumed.
- `backend/app/services/` — claim extraction, SSRF-safe URL fetch, end-to-end analyzer.
- `backend/app/schemas/` — Pydantic request/response contracts.
- `frontend/` — vanilla HTML/CSS/JS, no build step, served as static files.

## Milestone protocol

Milestones M0–M7 are defined in `PLAN.md`. Do not advance past a gate until its acceptance
criteria are verified with real commands. Status vocabulary: `NOT STARTED`, `IN PROGRESS`,
`BLOCKED`, `PASS`. Never mark `PASS` because code merely exists.

## Coding conventions

- Python 3.11, type hints on public functions, small focused modules.
- Pydantic v2 for all request/response schemas.
- No comments unless the logic is genuinely non-obvious. No dead code, no
  backwards-compatibility shims.
- Async I/O for network calls (`httpx`). Never block the event loop with model inference
  in a way that breaks concurrency expectations — inference is CPU-bound and synchronous;
  call it from a threadpool where it matters.
- Follow the existing structure; do not introduce microservices, message queues, vector
  databases, paid APIs, or multi-agent orchestration.

## Testing requirements

- `pytest` must pass with no network access (external calls mocked via `respx`).
- Live tests are marked `@pytest.mark.live` and only run with `-m live`.
- Every model has a load/inference test; the NLI label mapping has its own test.
- Failure paths (timeout, rate limit, malformed payload, model load error, empty evidence)
  are tested and must never fabricate output.
- Run `ruff check` before committing.

## Model & dataset policy

- Pretrained models only. No scratch training, no fine-tuning on evaluation data.
- Document model id + revision + license + size in `docs/EVALUATION.md`.
- FEVER is the evaluation benchmark (dev split, deterministic seed-42 stratified sample).
  Evaluation labels are never fabricated, and the eval sample is never used for tuning.

## Compute & cost budget

- CPU inference is the default; GPU optional. No paid service, database, or hosting.
- Keep any single model artifact at or under ~500 MB unless justified by measured value.
- Lazy-load models, cache embeddings, never load every model at once.
- Measure real size / RAM / latency; never assume what fits on the host.

## Security & secrets

- URL fetching must block private/loopback/link-local/metadata destinations, re-validate on
  every redirect, cap size and time, and allowlist content types.
- Never commit secrets. `.env` is gitignored; `.env.example` documents variable names only.
- Never echo tokens or secret environment values. Do not log request bodies that may
  contain private text beyond what is needed.

## Documentation standards

- Keep `README.md`, `AGENTS.md`, `PLAN.md`, `docs/PROJECT_STATUS.md` current.
- Distinguish **implemented**, **experimental**, and **planned** features explicitly.
- `docs/theory/` explains concepts actually used, with source references.
- `docs/experiments/` records real experiments only (question, setup, command, results, decision).

## GitHub & deployment rules

- Public repo `VerityAI` under the authenticated account, only after tests + secret scan pass.
- Never force-push or rewrite public history without a valid reason.
- Deploy on a verified free tier (Hugging Face Spaces Docker). If a tier cannot support the
  stack, report the exact limitation and deploy what fits — never claim full deployment.
- README must contain the actually verified public URLs.

## Prohibited

- Fabricating labels, evidence, citations, model metrics, source metadata, or results.
- Presenting a similarity/entailment/confidence score as the probability a claim is true.
- Replacing the pretrained pipeline with TF-IDF while describing it as fully semantic.
- Bypassing authentication, rate limits, robots restrictions, or payment requirements.

## Blockers

If an operation needs an interactive login, credential, payment decision, or account
privilege: stop only that operation, continue independent work, and record the exact
blocker in `docs/PROJECT_STATUS.md` with the action required.
