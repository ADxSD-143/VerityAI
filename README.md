---
title: VerityAI
emoji: 🔎
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

> The YAML block above is [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-config-reference)
> metadata used for the Docker deployment.

# VerityAI — evidence-grounded, multi-source claim checking

VerityAI takes a **claim**, a **paragraph/article**, or an **article URL**, retrieves real
evidence from permitted public sources, ranks it with a pretrained dense retriever (hybrid lexical +
semantic selectable), judges each passage against the claim with a pretrained NLI model, and returns
a **traceable** report.

**Core principle.** VerityAI evaluates claims against *retrieved evidence*. It does not know the
truth of every statement. A similarity, entailment or confidence score is never presented as the
probability that a claim is true.

## Features

- **Dense-first retrieval** — `BAAI/bge-small-en-v1.5` by default (measured best MRR on our
  benchmark); hybrid BM25 + BGE via Reciprocal Rank Fusion remains selectable
  (`VERITY_RETRIEVAL_MODE`), with optional cross-encoder reranking.
- **Pretrained NLI** — `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, premise = evidence passage,
  hypothesis = claim. Label order is read from the model config and unit-tested.
- **Real sources** — Wikipedia/MediaWiki, Wikidata, OpenAlex, and (optionally) Google Fact Check
  Tools (ClaimReview) or the Wikimedia **Wikinews** news source, each in its own adapter that fails
  soft.
- **Source independence** — near-duplicate / syndicated passages are clustered so copies are not
  counted as independent corroboration.
- **Conservative verdicts** — `SUPPORTED`, `REFUTED`, `INSUFFICIENT_EVIDENCE`,
  `CONFLICTING_EVIDENCE`, `UNABLE_TO_ASSESS`, `NOT_VERIFIABLE`. No verdict is forced on weak
  evidence.
- **Claim-type aware** — each statement is classified first (fact / opinion / prediction /
  allegation / unclear); non-fact statements return `NOT_VERIFIABLE` instead of a forced
  true/false verdict.
- **SSRF-safe URL fetching** — private/loopback/link-local/metadata destinations blocked, per-hop
  redirect validation, size/time caps, content-type allowlist.
- **Request protection** — per-client analysis rate limit, JSON body cap, body-read timeout and total analysis timeout.
- **No paid services** — CPU inference; no API keys required for the core pipeline.
- **Polished, accessible, build-free frontend** — vanilla HTML/CSS/JS served by the backend.

## Architecture

```
claim / text / url
   -> validation
   -> [url] SSRF-safe fetch + article extraction
   -> claim extraction (sentences + cautious claim filter)
   -> source adapters (concurrent): Wikipedia | Wikidata | OpenAlex | FactCheck?
   -> BGE dense (default)  |  BM25 + BGE RRF (hybrid)  ->  dedup  ->  optional rerank
   -> NLI (premise = passage, hypothesis = claim)
   -> source independence clustering
   -> conservative aggregation -> report
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for component boundaries and trade-offs.

## Model stack

| Stage | Model | Why |
|---|---|---|
| Dense retrieval | `BAAI/bge-small-en-v1.5` | strong small English retrieval model; ~130 MB; CPU-friendly |
| Lexical retrieval | `rank_bm25` (BM25Okapi) | exact names/dates/numbers that dense models blur |
| Fusion | Reciprocal Rank Fusion, k=60 | rank-based, no score calibration needed |
| Reranker (optional) | `cross-encoder/ms-marco-MiniLM-L-6-v2` | re-scores the top pool; off unless evaluation justifies it |
| NLI | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | entailment/neutral/contradiction over evidence-claim pairs |

No model is trained or fine-tuned. See [`docs/EVALUATION.md`](docs/EVALUATION.md) for measured
quality, sizes and latency.

## Quick start

Requires Python 3.10+ (3.11 recommended).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"          # add ",eval" for the evaluation scripts
```

Models download automatically on first use (~1 GB total) into the Hugging Face cache
(`HF_HOME`). To pre-download:

```bash
python -c "from app.models_io import get_sentence_transformer, get_nli_components; \
get_sentence_transformer('BAAI/bge-small-en-v1.5'); \
get_nli_components('MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli')"
```

### Run

```bash
python scripts/run_dev.py        # http://127.0.0.1:8000  (UI + API + /docs)
```

The first request is slower while the models load. `GET /health` reports which models are loaded.

### Configure (optional)

Copy `.env.example` to `.env`. Every value has a working default; the core pipeline needs no key.
`FACTCHECK_API_KEY` enables the ClaimReview source, `OPENALEX_MAILTO` joins the polite pool,
`HF_HOME` moves the model cache.

### Test

```bash
pytest -q                 # offline; external calls mocked with respx (live tests excluded)
pytest -q -m live         # opt-in real-network smoke tests (not run in CI)
ruff check backend experiments scripts
```

A manual, human-judged smoke-test checklist is in [`docs/SMOKE_TESTS.md`](docs/SMOKE_TESTS.md).

## Evaluation

Reproducible scripts live in [`experiments/`](experiments/README.md):

```bash
python experiments/build_fever_sample.py --limit 500 --seed 42
python experiments/eval_retrieval.py   --limit 500
python experiments/eval_nli.py
python experiments/eval_e2e.py
python experiments/measure_resources.py
```

Benchmark: FEVER development split, deterministic stratified sample of 500, seed 42. Results and
limitations: [`docs/EVALUATION.md`](docs/EVALUATION.md).

<!-- EVAL_SUMMARY_START -->
### Measured results (recorded; full protocol in `docs/EVALUATION.md`)

**Retrieval** — FEVER dev, 330 evaluable claims, 2409-page reconstructed corpus (harder run;
bootstrap 95% CIs in `docs/EVALUATION.md`):

| Retriever | Recall@5 | MRR |
|---|---|---|
| TF-IDF (baseline only) | 0.938 | 0.901 |
| BM25 | 0.916 | 0.858 |
| BGE dense (**default**) | **0.968** | **0.975** |
| Hybrid (BM25 + BGE, RRF k=60) | 0.946 | 0.955 |
| Hybrid + cross-encoder rerank | 0.965 | 0.966 |

Paired MRR difference (dense − hybrid) = +0.020, 95% CI [0.003, 0.038] → dense-only is the default.

**NLI** — 493 claims:

| Model | Accuracy | Macro-F1 |
|---|---|---|
| `DeBERTa-v3-base-mnli-fever-anli` (default) | **0.675** | **0.671** |
| `nli-deberta-v3-small` (documented fallback) | 0.448 | 0.458 |

**End-to-end** — 8 hand-labelled live claims: **4/8** matched the expected status (original run;
the single-source safeguard was added afterwards — see the limitations below).
<!-- EVAL_SUMMARY_END -->

## Deployment

<!-- DEPLOY_URL_START -->
Not yet deployed. Target: Hugging Face Spaces (Docker). The verified public URL will be recorded
here once the deployment is confirmed.
<!-- DEPLOY_URL_END -->

Build/run the container locally:

```bash
docker build -t verityai .
docker run -p 7860:7860 verityai      # http://127.0.0.1:7860
```

## Capability status

Honest matrix — a capability counts as done only when it is implemented, tested and documented
(full table in [`docs/READINESS.md`](docs/READINESS.md)).

| Capability | Status |
|---|---|
| Text / claim / URL checking | Implemented · tested · live-verified |
| Request limits (rate / body / timeouts) | Implemented · tested |
| SSRF-safe URL fetch | Implemented · tested |
| Source independence + aggregation safeguard | Implemented · tested (one live re-check) |
| Retrieval (dense default; hybrid selectable) | Implemented · evaluated with bootstrap CIs |
| NLI (base model) | Evaluated with CIs · small model blocked on this host |
| Claim-type classification + allegation handling | Implemented · tested · **accuracy not yet evaluated** |
| Provenance / recency disclosure | Implemented · tested |
| Hindi / Hinglish | Accepted, but non-English input returns `UNABLE_TO_ASSESS` with a language disclosure (models are English-first) · **verdict quality unverified** |
| Held-out end-to-end evaluation | **Blocked** on human-reviewed labels |
| `tau_single` tuning | **Blocked** on a reviewed tuning split |
| Media (OCR) and live checking | Planned |
| Public deployment | **Blocked** on Hugging Face credentials |

## Limitations and known failure modes

- Retrieval covers only the configured permitted sources — **not the entire internet**.
- NLI scores are per evidence-claim pair, not truth probabilities; models can be wrong, especially
  on numeric, temporal and negation-heavy claims.
- **Single-source verdicts are gated**: a verdict resting on one independent source must clear a
  higher NLI bar (`tau_single`, default 0.75) or it returns `INSUFFICIENT_EVIDENCE`. This closes a
  recorded false positive — *"Zorbax-9 was the first spacecraft to land on the Sun"* was once
  reported `SUPPORTED` from a single passage (entailment 0.52); re-checked live after the fix it
  returns `INSUFFICIENT_EVIDENCE`. A confident single-source error (score ≥ 0.75) is still possible.
- Retrieval can pull a *different entity* with a similar name (the Eiffel Tower page vs Eiffel Tower
  (Paris, Texas)), which can surface as `CONFLICTING_EVIDENCE` for an otherwise simple claim.
- English-first. Non-English input is detected and returned as `UNABLE_TO_ASSESS` with a
  disclosure instead of a possibly-wrong verdict, because the pretrained models cannot assess it.
  Detection covers a majority non-Latin script and Roman-script Hinglish, but **not** other
  Latin-script languages (e.g. French or German), which are still treated as English
  (see [`docs/EVALUATION.md`](docs/EVALUATION.md)).
- FEVER-retrieval results do not imply real-world accuracy for current events or arbitrary sites.
- Rate limiting is process-local and based on the socket peer IP; proxies may cause shared buckets, and multiple workers do not share counters.
- DNS-rebinding TOCTOU on URL fetch is mitigated, not eliminated (see
  [`docs/SECURITY.md`](docs/SECURITY.md)).

## Licenses

- Project code: MIT (see [`LICENSE`](LICENSE)).
- Models: use each model card's license (`bge-small-en-v1.5` MIT; `ms-marco-MiniLM-L-6-v2`
  Apache-2.0; `DeBERTa-v3-base-mnli-fever-anli` MIT).
- FEVER dataset: CC BY-SA 3.0.

## Development

See [`AGENTS.md`](AGENTS.md) for conventions, [`PLAN.md`](PLAN.md) for the milestone plan, and
[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the current resumable state.
