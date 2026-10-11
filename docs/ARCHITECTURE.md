# Architecture

## What VerityAI is

VerityAI evaluates a claim against **retrieved evidence**. It extracts claims, retrieves
passages from permitted public sources, ranks them with a pretrained dense retriever (hybrid
lexical + semantic is selectable), judges each passage against the claim with a pretrained NLI
model, clusters evidence by source independence, and produces a conservative, traceable report.

It does not "know" truth and it does not report a probability that a claim is true.

## Request flow

```
POST /api/analyze {claim | text | url}
  -> input validation (exactly one field)
  -> [url] SSRF-safe fetch + article extraction
  -> claim extraction (single claim kept verbatim; long text segmented + filtered)
  -> claim-type classification (rules): fact | opinion | prediction | allegation | unclear
     (non-fact claims short-circuit to NOT_VERIFIABLE, no retrieval)
  -> for each fact claim:
       source adapters (concurrent): Wikipedia | Wikidata | OpenAlex | (optional) FactCheck
       -> candidate passages (sentence-level, with provenance)
       -> BGE dense ranking (default)  |  BM25 + BGE via RRF (hybrid, VERITY_RETRIEVAL_MODE)
       -> deduplicate (near-duplicate removal)
       -> optional cross-encoder rerank of the top pool
       -> NLI (premise = passage, hypothesis = claim) on the top candidates
       -> source independence clustering (document + near-duplicate merge)
       -> conservative aggregation -> verdict + explanation
  -> structured report (evidence, sources queried, failures, limitations)
```

## Components

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | App factory, CORS, error handlers, static frontend mount |
| `backend/app/api/routes.py` | `/health`, `/api/analyze`, `/api/analyze-url` |
| `backend/app/config.py` | Environment-driven settings (all optional) |
| `backend/app/core/limits.py` | Per-client rate limit, body-size + read-time caps, typed 408/413/429 |
| `backend/app/core/errors.py` | Typed error hierarchy (`unsafe_url`, `url_fetch_failed`, `model_load_failed`, `analysis_timeout`, ...) |
| `backend/app/core/text.py` | Deterministic segmentation, tokenization, shingles, entity hints |
| `backend/app/schemas/models.py` | Pydantic v2 request/response contracts |
| `backend/app/sources/` | One adapter per external source (see below) |
| `backend/app/retrieval/` | `lexical` (BM25), `dense` (BGE), `fusion` (RRF), `rerank` (cross-encoder), `pipeline` |
| `backend/app/analysis/` | `nli`, `independence`, `aggregation` |
| `backend/app/services/` | `claim_extraction`, `claim_type` (rules classifier), `url_extract` (SSRF-safe), `analyzer` (orchestration) |
| `backend/app/models_io.py` | Lazy, process-wide model registry with failure caching |
| `frontend/` | Vanilla HTML/CSS/JS single page, no build step |

### Source adapters

Each adapter implements `search(claim, queries, client) -> SourceResult` and fails soft
(returns `status="error"`, never raising into the request). What each returns:

- **Wikipedia / MediaWiki** — original evidence. Search + plain-text extracts, split into
  sentence-level passages with page id, title, canonical URL and retrieval timestamp.
- **Wikidata** — original structured facts ("Douglas Adams: date of birth — 1952-03-11.").
- **OpenAlex** — original scholarly titles/abstracts (inverted index reconstructed).
- **Google Fact Check Tools (ClaimReview)** — a *publisher verdict*, not original evidence;
  enabled only when `FACTCHECK_API_KEY` is set, and shown separately from our NLI assessment.
- **Wikinews** — optional news-style source on the identical MediaWiki API; **off by default**
  (`VERITY_ENABLE_WIKINEWS`), because its evidence value is not yet measured.

## Retrieval

- **Lexical**: `rank_bm25.BM25Okapi` over tokenized passages. Keeps exact names, dates,
  numbers and technical terms retrievable.
- **Dense**: `BAAI/bge-small-en-v1.5`. Queries get the model card's instruction prefix;
  passages are encoded plain; both are L2-normalized so cosine similarity is a dot product.
  Embeddings are cached in memory and (optionally) on disk, keyed by `sha256(model_id + text)`.
- **Fusion**: Reciprocal Rank Fusion `mean 1/(k + rank)`, `k=60`. RRF combines by rank, so
  BM25's unbounded scores are never mixed with cosine similarities.
- **Deduplication**: near-duplicate passages (5-gram Jaccard ≥ 0.8) are removed after fusion.
- **Reranking** (optional): `cross-encoder/ms-marco-MiniLM-L-6-v2` over the top pool. Included
  in the default runtime only if the evaluation justifies the added latency.

If the dense model cannot load, the pipeline degrades to BM25-only and sets
`meta.degraded_mode` with the reason — it never silently pretends to be semantic.

## NLI and aggregation

`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` with `premise = passage`, `hypothesis = claim`.
The class order is read from the loaded `config.id2label` and validated against the three
canonical labels (`entailment`, `neutral`, `contradiction`); an unresolvable mapping is a
load error, not a silent mis-label. Scores are model outputs for a specific pair, never a
truth probability.

Aggregation is explicit rule-based (see `docs/theory/evidence-aggregation.md`):

| Situation | Status |
|---|---|
| no strong evidence either way | `INSUFFICIENT_EVIDENCE` |
| non-fact statement (opinion / prediction / allegation / unclear) | `NOT_VERIFIABLE` (no retrieval, no true/false) |
| strong support **and** strong contradiction | `CONFLICTING_EVIDENCE` |
| strong support only, corroborated or single source with score ≥ `tau_single` | `SUPPORTED` (flagged `limited_corroboration` if < 2 independent sources) |
| strong support only, single source with score < `tau_single` | `INSUFFICIENT_EVIDENCE` |
| strong contradiction only | `REFUTED` (same single-source rule) |
| all sources unreachable | `UNABLE_TO_ASSESS` |

## Failure paths

- A source that errors is recorded in `sources_queried` and `source_failures`; other sources
  still contribute. No evidence is invented.
- A model that fails to load sets `degraded_mode` and produces `UNABLE_TO_ASSESS` for the
  affected claim rather than a guessed label.
- URL fetch failures return a typed HTTP error (`unsafe_url`, `url_fetch_failed`) with a safe
  message; no stack traces or local paths are exposed.
- Request limits run before the handler: oversized or streamed bodies → 413, a body that never
  arrives → 408, too many requests from one client → 429 (with `Retry-After`), and a slow
  analysis → typed 504. `/health` and static assets are never rate limited.
- A verdict resting on a **single independent source** must clear the higher `tau_single` bar,
  otherwise it is reported as `INSUFFICIENT_EVIDENCE` rather than a forced verdict.

## Trade-offs

- **Sentence-level passages** give precise NLI premises and cheap provenance, at the cost of
  losing cross-sentence context.
- **Wikipedia reconstruction** in the evaluation avoids a multi-GB FEVER dump, at the cost of
  page-level (not sentence-level) relevance and non-frozen page text.
- **Two models** (dense + NLI) fit comfortably on a free CPU host; a larger dense model was
  left out because it is not needed for the measured quality.
- **Deterministic regex segmentation** instead of a transformer segmenter keeps the pipeline
  dependency-light and reproducible.
