# API

Base URL (local): `http://127.0.0.1:8000`. Interactive docs: `/docs`.

All responses are JSON. Errors share one shape:

```json
{ "error": "human-readable message", "code": "machine_code", "details": {} }
```

| Code | HTTP | Meaning |
|---|---|---|
| `invalid_input` | 422 | Request failed validation |
| `unsafe_url` | 400 | URL blocked by the SSRF guard |
| `url_fetch_failed` | 502 | Fetch/extraction failed |
| `model_load_failed` | 503 | A required model could not load |
| `source_error` | 502 | Upstream source error |
| `rate_limited` | 429 | Per-client request cap exceeded (includes `Retry-After`) |
| `request_too_large` | 413 | Request body exceeds the configured size limit |
| `invalid_content_length` | 400 | Malformed `Content-Length` header |
| `request_body_timeout` | 408 | Body did not arrive within the read timeout |
| `analysis_timeout` | 504 | Analysis exceeded the configured time limit |

## `GET /health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "device": "cpu",
  "models_loaded": ["nli:MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli@default"],
  "uptime_s": 12.4,
  "timestamp": "2026-01-01T00:00:00+00:00"
}
```

`models_loaded` lists what has actually been loaded so far (models load lazily).

## `POST /api/analyze`

Exactly one of `claim`, `text`, `url` must be provided.

```json
{
  "claim": "The Eiffel Tower is located in Paris.",
  "options": {
    "max_claims": 5,
    "top_k_retrieval": 10,
    "top_k_nli": 6,
    "use_reranker": false
  }
}
```

`options` is optional; omitted fields fall back to configuration.

### Response

```jsonc
{
  "input": { "kind": "claim", "value_preview": "...", "characters": 38 },
  "claims": [
    {
      "claim_id": "c1",
      "text": "The Eiffel Tower is located in Paris.",
      "start": null, "end": null,
      "status": "SUPPORTED",
      "claim_type": "CHECKABLE_FACT",
      "explanation": "2 passage(s) from 2 independent source(s) entail the claim ...",
      "limited_corroboration": false,
      "claim_notes": ["entities: Eiffel Tower, Paris"],
      "stats": {
        "passages_considered": 6, "support_passages": 2, "contradict_passages": 0,
        "support_sources": 2, "contradict_sources": 0, "independent_groups": 3
      },
      "supporting": [ /* EvidenceItem */ ],
      "contradicting": [],
      "neutral": [ /* EvidenceItem */ ],
      "fact_checks": [ /* FactCheckItem, if configured */ ]
    }
  ],
  "sources_queried": [
    { "source": "wikipedia", "endpoint": "...", "queries": ["..."],
      "status": "ok", "n_results": 42, "error": null }
  ],
  "source_failures": [],
  "meta": {
    "analysis_id": "a1b2c3d4e5f6",
    "created_at": "2026-01-01T00:00:00+00:00",
    "processing_ms": 4210,
    "degraded_mode": false,
    "degraded_reasons": [],
    "models": [ { "name": "nli", "model_id": "...", "role": "...", "device": "cpu", "loaded": true } ],
    "limitations": [ "..." ]
  }
}
```

### `EvidenceItem`

| Field | Meaning |
|---|---|
| `passage` | The evidence sentence |
| `source`, `title`, `url`, `publisher` | Provenance (clickable in the UI) |
| `published_at`, `retrieved_at` | Dates where available |
| `rank`, `retrieval_score` | Position and fused/reranked relevance |
| `bm25_rank`, `dense_rank`, `rrf_score`, `rerank_score` | Per-stage diagnostics |
| `nli_label`, `nli_score`, `nli_probs` | NLI output for *this* passage-claim pair |
| `independent_group` | Cluster id used for source-independence counting |
| `note` | e.g. "title-only record (no abstract available)" |

`nli_score` is a model output for an evidence-claim pair. It is **not** the probability
that the claim is true.

### Statuses

`SUPPORTED`, `REFUTED`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`, `UNABLE_TO_ASSESS`,
`NOT_VERIFIABLE`.

`UNABLE_TO_ASSESS` is returned both when the evidence pipeline cannot complete (no source
reachable, or the NLI model unavailable) and when the input is not in a language the pretrained
models support (they are English-first); the `explanation` discloses which case applies.

### Claim types

Each claim carries a `claim_type` (deterministic rules classifier):

- `CHECKABLE_FACT` — runs the evidence pipeline and can receive a `SUPPORTED`/`REFUTED` verdict.
- `OPINION_SUBJECTIVE`, `PREDICTION`, `UNCLEAR` — **no retrieval**; return `NOT_VERIFIABLE`.
- `ALLEGATION` — runs the pipeline but is **always** `NOT_VERIFIABLE`; the explanation and notes
  report how many passages support/contradict and whether an *official-finding* signal appears,
  and never declare the allegation true or false.

`NOT_VERIFIABLE` means the statement is not the kind of claim this system verifies; it is not a
judgement about the statement's truth.

## `POST /api/analyze-url`

Thin wrapper that forces `url` input:

```json
{ "url": "https://example.com/article", "options": { "max_claims": 3 } }
```

Returns the same `AnalysisReport`. Unsafe or unreachable URLs return `unsafe_url` (400) or
`url_fetch_failed` (502).

## Example

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"claim":"The Eiffel Tower is located in Paris."}'
```
