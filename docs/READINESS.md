# VerityAI readiness report

Snapshot: `main` = `875f042` (public repo `ADxSD-143/VerityAI`), working tree clean at audit time.
This report separates verified facts, historical results, unverified assumptions, missing evidence
and owner blockers. It does not replace `docs/PROJECT_STATUS.md`.

## Verified facts (evidence)

- **Repo/CI**: repo is public; GitHub Actions CI is green on the current `main` (`89f402f`, run
  `38114131072`) and on prior commits (verified via the GitHub Actions API).
- **Offline suite**: `ruff check backend experiments scripts` clean; `pytest -q` → **148 passed**
  (verified locally on this host, `VERITY_PRELOAD_MODELS=false`, no network).
- **Live smoke tests** (opt-in): `pytest -q -m live` → **3 passed** in 27 s — the real Wikipedia and
  Wikinews adapters return evidence with provenance, and the full `/api/analyze` pipeline runs end
  to end. `live` tests are excluded from the default run (`addopts = -q -m "not live"`), so CI stays
  offline.
- **Request hardening is implemented and tested** (`backend/app/core/limits.py`,
  `backend/app/main.py`, `backend/app/api/routes.py`): per-client sliding-window rate limit on
  `/api/analyze` and `/api/analyze-url`, JSON body cap, body-read timeout, total analysis timeout,
  typed 413/408/429/504 errors. Tests: `backend/tests/test_limits.py`, `test_timeouts.py`.
- **Aggregation safeguard**: single-independent-source verdicts require `tau_single` (0.75) else
  `INSUFFICIENT_EVIDENCE` (`backend/app/analysis/aggregation.py`); regression test
  `backend/tests/test_aggregation_regression.py`.
- **Retrieval default is now dense-only** from measured data (`verity_retrieval_mode="dense"`,
  `backend/app/retrieval/pipeline.py`); BM25 retained as the dense-failure fallback.
- **SSRF controls** implemented and unit-tested (`backend/app/services/url_extract.py`,
  `backend/tests/test_url_safety.py`): scheme/port allowlist, no credentials, all resolved IPs
  checked (incl. IPv4-mapped/6to4/teredo), per-hop redirect re-validation, size/time caps,
  content-type allowlist.

## Historical results (with provenance)

- **Retrieval (superseded)**: 330 claims / 1161-page corpus; BGE MRR 0.985 (seed 42, sample 500).
- **Retrieval (current)**: 330 claims / 2409-page corpus (367 gold + 2042 distractors; 483
  unavailable); bootstrap 95% CIs recorded in `experiments/results/eval_retrieval.json` and
  `docs/EVALUATION.md`. BGE dense R@5 0.968 [0.952, 0.981], MRR 0.975 [0.961, 0.987]; hybrid MRR
  0.955 [0.935, 0.974]; paired MRR diff (dense−hybrid) +0.0196 [0.0027, 0.0377].
- **NLI (point estimates, pre-CI)**: base accuracy 0.675 / macro-F1 0.671; small 0.448 / 0.458
  (`experiments/results/eval_nli.json`, `eval_nli_small.json`).
- **End-to-end (diagnostic)**: 8 hand-labelled live claims, 4/8 matched
  (`experiments/results/eval_e2e.json`); Zorbax-9 re-checked once after the safeguard →
  `INSUFFICIENT_EVIDENCE`.
- **Resources**: BGE 134.5 MB, NLI base 380 MB, reranker 91.8 MB (`measure_resources.json`).

## Unverified assumptions

- Hybrid's "exact-term robustness" on live text is **untested**; the page-level benchmark does not
  measure it. It is no longer the default.
- The live 8-claim e2e has **not** been re-run under the dense default, so the dense switch's live
  effect is unmeasured.
- Hindi/Hinglish performance is **not** established (FEVER is English).

## Missing evidence

- NLI **bootstrap CIs**: base DONE (accuracy **0.675 [0.633, 0.716]**, macro-F1 **0.671
  [0.630, 0.712]**); the small candidate is **BLOCKED** on this host (sentencepiece DLL blocked by the
  Application Control policy).
- **Human-reviewed held-out labels** (≥60). Drafted candidates exist
  (`data/annotations/phase0_candidates.csv`, 100 proposed rows, 62 held-out / 38 tuning) but are
  machine-proposed and **not gold**. Annotation validation tooling now exists
  (`experiments/annotation_tools.py`) and rejects cross-split leakage; the held-out harness
  (`experiments/eval_e2e_heldout.py`) refuses to score until the gate passes.
- `tau_single` tuning on a tuning split (blocked on the reviewed labels).
- Deployment verification (no live URL).

## Blockers requiring the project owner

1. **Human annotation review** of `data/annotations/phase0_candidates.csv` → promote verified rows
   into `phase0_e2e_template.csv`. Required before any tuning/held-out metric.
2. **Hugging Face write credentials + authorization** to create the Space (M7 deploy). No token on
   this host.
3. **Authorization** for any paid/external resources (none required so far).
4. **Host policy**: the Windows Application Control policy blocks the `sentencepiece` DLL, so the
   DeBERTa-v2 small NLI candidate cannot load here. Evaluate it on a host with a permissive policy.

## Capability matrix

| Capability | Implemented | Tested | Evaluated | Deploy-verified | Status |
|---|---|---|---|---|---|
| Text/claim/URL checking | yes | yes | partial (e2e 8) | no | Active |
| Rate limiting / size+time caps | yes | yes | n/a | no | Active |
| SSRF-safe URL fetch | yes | yes | n/a | no | Active |
| Privacy / log hygiene | yes | yes | n/a | no | Active |
| Source adapters (OpenAlex/Wikidata/FactCheck) | yes | yes | n/a | no | Active |
| Partial source failure (one adapter down) | yes | yes | n/a | no | Active |
| Error paths (model load / URL fetch failure) | yes | yes | n/a | no | Active |
| Aggregation safeguard | yes | yes | 1 live re-check | no | Active |
| Dense retrieval default | yes | yes | yes (CIs) | no | Active |
| NLI base / small | yes | yes | base CIs done; small blocked (host) | no | Base active; small blocked |
| Held-out labelled set | template+draft | n/a | no | n/a | Awaiting review (owner) |
| `tau_single` tuning | no | n/a | no | n/a | Blocked on labels |
| News source: Wikinews (Phase 1) | yes (opt-in) | yes (mock + live) | value unmeasured | no | Active, off by default |
| Provenance / recency disclosure | yes | yes | n/a | no | Active |
| Claim-type classifier (Phase 2) | yes (rules) | yes | **pending** (needs labelled set) | no | Implemented; evaluation blocked |
| Allegation handling (Phase 2) | yes | yes | n/a | no | Active (never true/false) |
| Hindi/Hinglish (Phase 3) | partial (Unicode tokenization + claim-detection heuristic) | yes | no | no | Planned (models English-first) |
| Media OCR (Phase 4) | no | no | no | no | Planned |
| Live checking (Phase 5) | no | no | no | no | Planned |
| Public deployment | config ready | no | no | no | Blocked (HF token) |

## Severity-ranked findings

1. **High — evaluation foundation incomplete.** No human-reviewed held-out set; `tau_single` tuned
   on a single example. Fix: owner reviews candidates; add tooling to score a held-out run; tune
   only on the tuning split. Acceptance: ≥60 reviewed held-out rows; held-out metrics with CIs;
   tuning separated.
2. **Medium — NLI results.** Base re-run now has CIs (0.675 [0.633, 0.716]); the small candidate
   cannot load on this host (sentencepiece blocked). Remaining: peak-RAM numbers and a small-model
   run on a permissive host. Acceptance: both candidates with CIs + RAM in `docs/EVALUATION.md`.
3. **Medium — deploy unverified.** Fix: owner supplies HF token; then verify `/health`, one real
   analysis, and a failure path before advertising. Acceptance: responsive public URL recorded.
4. **Low — stale-ish docs drift** as parallel sessions commit. Fix: keep `PROJECT_STATUS.md`
   authoritative and update on each change. Acceptance: status matches `main`.
5. ~~**Medium — Latin-only tokenizer.**~~ **FIXED (2026-10-11).** `tokenize` is now Unicode-aware
   (`[^\W_]+`); `shingles` returns an empty set for token-less text, and `jaccard` treats an empty
   shingle set as "no comparable content" (0.0) instead of 1.0. Distinct non-Latin or
   punctuation-only passages are therefore no longer merged into one "independent" source.
   Regression tests: `test_distinct_non_latin_passages_are_independent`,
   `test_identical_non_latin_passages_merge`, and text-level tests. Still open (Phase 3):
   `looks_like_claim`'s verb hint is Latin-only, so pure-Hindi claims are not extracted.
