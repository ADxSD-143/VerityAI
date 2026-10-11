# VerityAI readiness report

Snapshot: `main` = `875f042` (public repo `ADxSD-143/VerityAI`), working tree clean at audit time.
This report separates verified facts, historical results, unverified assumptions, missing evidence
and owner blockers. It does not replace `docs/PROJECT_STATUS.md`.

## Verified facts (evidence)

- **Repo/CI**: repo is public; GitHub Actions CI runs #10 (`d16ebe4`) and #11 (`38d4e6f`) both
  **success** (verified via the GitHub Actions API).
- **Offline suite**: `ruff check backend experiments scripts` clean; `pytest -q` → **83 passed**
  (verified locally on this host, `VERITY_PRELOAD_MODELS=false`, no network).
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
  (`experiments/annotation_tools.py`) and rejects cross-split leakage.
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
| Aggregation safeguard | yes | yes | 1 live re-check | no | Active |
| Dense retrieval default | yes | yes | yes (CIs) | no | Active |
| NLI base/small | yes | yes | CIs this cycle | no | In progress |
| Held-out labelled set | template+draft | n/a | no | n/a | Awaiting review (owner) |
| `tau_single` tuning | no | n/a | no | n/a | Blocked on labels |
| Web/news adapter (Phase 1) | no | no | no | no | Planned |
| Claim-type classifier (Phase 2) | no | no | no | no | Planned |
| Hindi/Hinglish (Phase 3) | experimental | no | no | no | Planned |
| Media OCR (Phase 4) | no | no | no | no | Planned |
| Live checking (Phase 5) | no | no | no | no | Planned |
| Public deployment | config ready | no | no | no | Blocked (HF token) |

## Severity-ranked findings

1. **High — evaluation foundation incomplete.** No human-reviewed held-out set; `tau_single` tuned
   on a single example. Fix: owner reviews candidates; add tooling to score a held-out run; tune
   only on the tuning split. Acceptance: ≥60 reviewed held-out rows; held-out metrics with CIs;
   tuning separated.
2. **Medium — NLI results lack CIs/RAM.** Fix: re-run both candidates with the (already wired)
   bootstrap CIs and record peak RAM. Acceptance: CIs + latency + RAM in `docs/EVALUATION.md`.
3. **Medium — deploy unverified.** Fix: owner supplies HF token; then verify `/health`, one real
   analysis, and a failure path before advertising. Acceptance: responsive public URL recorded.
4. **Low — stale-ish docs drift** as parallel sessions commit. Fix: keep `PROJECT_STATUS.md`
   authoritative and update on each change. Acceptance: status matches `main`.
5. **Medium — Latin-only tokenizer.** `app.core.text.tokenize` matches only `[A-Za-z0-9]`, so
   non-Latin text tokenizes to nothing and `shingles` / `analysis/independence` collapse distinct
   passages (Jaccard 1.0), which would overstate corroboration. Affects Hindi/Hinglish (Phase 3).
   Fix: script-aware tokenization/shingling + a regression test. Acceptance: distinct non-Latin
   passages are not merged into one independent source.
