# VerityAI Project Status

## Last Updated
2026-10-14 (Asia/Kolkata)

## Current Milestone
Product Phase 0 — reliability hardening **IN PROGRESS**. Historical M0–M6 are complete; M7 deployment remains pending on a Hugging Face token.

## Overall Status
The public repository and CI are verified. Phase 0 hardening is active. Deployment remains blocked on credentials; the larger-corpus evaluation and human-labelled held-out set are outstanding.

## Environment
- **OS**: Windows (win32), PowerShell 5.1, repo `D:\project ideas\VerityAI`.
- **Python**: 3.11.7 in `.venv` (deps installed from a PyPI **mirror**; PyPI's CDN was ~33 KB/s here).
- **Key versions**: `torch 2.14.1+cpu`, `transformers 4.57.6`, `sentence-transformers 3.4.1`,
  `numpy 2.4.6`, `scikit-learn 1.5.2`, `pandas 2.2.3`, `pyarrow 17.0.0`, `datasets 2.21.0`.
- **Node**: v24.15.0 (unused — vanilla frontend). **git**: 2.55.0.
- **GitHub**: repo **published** (public). `gh` CLI still **not installed** on this host; the push
  used an existing git credential.
- **Hugging Face**: **no token** (no `HF_TOKEN`, no cached login). **Docker**: **not installed**.
- **Compute**: i7-12650HX (14c/20t), 15.73 GB RAM, CPU-only inference. `HF_HOME=D:\hf-cache`.

## Completed
- **M0** audit + control files.
- **M1** — app verified end-to-end (live `/api/analyze` with real Wikipedia + Wikidata + OpenAlex
  evidence, SSRF + validation paths).
- **M2** — BGE dense + BM25 + RRF + dedup + optional reranker implemented; retrieval benchmark run
  (330 evaluable claims, 1161-page corpus).
- **M3** — NLI implemented with config-read label map; NLI benchmark run for base and small.
- **M4** — FEVER `labelled_dev` sample (500, seed 42), all evaluation artefacts saved.
- **M5** (code) — SSRF-safe URL extraction + tests; secret scan clean.
- **M6** (code/docs/CI) — full docs set, CI workflow, Dockerfile, README Spaces frontmatter; **CI
  verified green on GitHub** (green at M6 completion on `38d4e6f`; latest verified run #43 on
  `4f2a9f2` ⇒ success, 2026-10-12).
- **M7 (part)** — **GitHub publication**: public repo at
  [`github.com/ADxSD-143/VerityAI`](https://github.com/ADxSD-143/VerityAI), `main` = `4f2a9f2` (2026-10-12).
- **Aggregation safeguard** — single-source verdicts must clear `tau_single` (default 0.75); adds
  `backend/tests/test_aggregation_regression.py`. Closes the recorded Zorbax-9 false positive
  (re-checked live: now `INSUFFICIENT_EVIDENCE`, best entailment 0.519).

## In Progress
- **M7 (deployment half)** — Hugging Face Space deployment. **Pending**, blocked on HF credentials.

## Next Actions
1. Authenticate Hugging Face and create the Docker Space:

   ```powershell
   pip install "huggingface_hub[cli]"
   huggingface-cli login               # needs your write token
   huggingface-cli repo create VerityAI --type space --space_sdk docker
   git remote add space https://huggingface.co/spaces/<your-account>/VerityAI
   git push space main
   ```

2. After deploy: verify the public frontend + `/health` + one real analysis, then replace the
   `DEPLOY_URL` placeholder in `README.md` and record the URL here.
3. (Optional) install Docker Desktop if a local image build is wanted; HF Spaces builds it
   server-side regardless.

## Milestone Gates
- M0 **PASS** · M1 **PASS** · M2 **PASS** · M3 **PASS** · M4 **PASS** · M5 **PASS** ·
  M6 **PASS** (CI verified on GitHub) · M7 **IN PROGRESS** (GitHub publication verified; HF
  deployment pending on credentials).

## Tests and Verification
| Command | Outcome |
|---|---|
| `ruff check backend experiments scripts` | All checks passed |
| `pytest -q` (181 tests) | exit code 0, all passed |
| `pytest -q -m live` (3 tests) | 3 passed in 27 s (Wikipedia + Wikinews adapters + full `/api/analyze`); opt-in, excluded from CI |
| `POST /api/analyze` (live) | 200, real multi-source evidence |
| `POST /api/analyze-url` (metadata IP) | 400 `unsafe_url` |
| secret scan (grep + `git ls-files`) | clean; no `.env`; no tracked file > 1 MB |
| GitHub Actions CI (run #43, `4f2a9f2`, 2026-10-12) | **success** |
| `docker build` | **not run** — Docker is not installed on this host |

## Evaluation
All artefacts in `experiments/results/`:
- `fever_sample.json` — 500 claims, seed 42, labels 166 REFUTES / 167 SUPPORTS / 167 NEI; 367 gold
  pages + 2525 distractors (the deterministic pool caps at 2525; a 5000 request is pool-limited).
- `eval_retrieval.json` — **harder corpus**: 330 evaluable claims, **2409 usable pages** (367 gold +
  2042 distractors; 483 unavailable). Bootstrap 95% CIs: BGE dense R@5 0.968 [0.952, 0.981], MRR
  **0.975 [0.961, 0.987]**; hybrid R@5 0.946 [0.923, 0.967], MRR 0.955 [0.935, 0.974]; paired MRR
  difference (dense − hybrid) **+0.0196 [0.0027, 0.0377]**.
- `eval_nli.json` (base) — accuracy **0.675 [0.633, 0.716]**, macro-F1 **0.671 [0.630, 0.712]**,
  mean latency 159.9 ms/pair (contended host).
- `eval_nli_small.json` (small) — **not reproducible on this host** (sentencepiece DLL blocked by
  the Application Control policy); historical point estimates 0.448/0.458, no CI.
- `eval_e2e.json` — 4/8 live claims matched (original run; unchanged). **Live re-check (single
  observation)** of the one false positive after adding the safeguard: Zorbax-9 →
  `INSUFFICIENT_EVIDENCE` (best entailment 0.519 < `tau_single` 0.75).
- `measure_resources.json` — BGE 134.5 MB, NLI 380.0 MB, reranker 91.8 MB (all < 500 MB budget).

## Decisions
- Default retrieval = **dense-only** (`VERITY_RETRIEVAL_MODE=dense`), chosen from the harder-corpus
  paired CI (dense beats hybrid on MRR; interval excludes zero). `hybrid` BM25+BGE RRF remains
  selectable; BM25 is the dense-failure fallback. The old exact-term-robustness rationale for hybrid
  is an untested live-setting hypothesis, not a measured win. Reranker **off** by default.
- Default NLI = base model (clearly better than the small model on this host).
- **Aggregation safeguard** = a verdict on a single independent source needs a higher NLI bar
  (`verity_tau_nli_single_source`, default 0.75) else `INSUFFICIENT_EVIDENCE`. A principled default,
  **not** tuned on the 8-claim set. Documented trade-off: single-weak-source claims now report as
  insufficient (precision↑/recall↓ for `SUPPORTED`).
- Aggregation policy **not** tuned on the 8-claim e2e set.
- Pinned older sklearn/pandas/pyarrow for Windows Application Control compatibility.

## Blockers
1. **No Hugging Face token** — blocks Space creation/upload. Action: `huggingface-cli login` (write
   token) or set `HF_TOKEN`.
2. **Docker not installed** — the image cannot be built locally; HF Spaces builds it server-side.
   Action: install Docker Desktop if local build validation is wanted.
(Resolved: `gh`/GitHub publication — the repo is public and CI is green.)

## GitHub
**Published**: [`github.com/ADxSD-143/VerityAI`](https://github.com/ADxSD-143/VerityAI), public,
default branch `main`; last verified CI run #43 on `4f2a9f2` (2026-10-12) = success.

## Deployment
Not deployed. `Dockerfile` + README Spaces frontmatter are ready (port 7860). Public URL to be
recorded here and in `README.md` once verified.

## Resume Instructions
GitHub publication and CI are done and verified — do not repeat them. To finish M7: authenticate
Hugging Face, create the Docker Space, push, then verify the public frontend, `/health`, and one
real analysis and write the URL into `README.md` (`DEPLOY_URL`). Do not re-run the environment
audit, the benchmark evaluations, or re-create the control files. Restart the server with:
`$env:HF_HOME="D:\hf-cache"; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`.


## Product Phase 0 checkpoint — 2026-10-10

**Current phase:** Phase 0 — reliability hardening; IN PROGRESS.

**Changes prepared in branch phase0/hardening-evaluation:**
- Process-local per-client sliding-window rate limiting on /api/analyze and /api/analyze-url (default 10 requests / 60 seconds).
- Request-body cap (1,000,000 bytes), body-read timeout (5 seconds), total analysis timeout (60 seconds), and typed 413/408/429/504 errors.
- Candidate NLI config-label mapping tests for both recorded model candidates.
- Evaluation scripts now calculate deterministic percentile bootstrap 95% CIs; fresh reruns remain necessary for the harder-corpus results and current latency intervals.
- FEVER training-contamination warning added to evaluation documentation.
- Annotation template is intentionally blank; labels are not fabricated.
- Annotation **validation + leakage tooling** and the **held-out harness** (`experiments/annotation_tools.py`, `experiments/eval_e2e_heldout.py`); the harness refuses to score unreviewed/under-sized sets.
- **Script-aware tokenization** fixes non-Latin source independence (`app/core/text.py`); distinct Devanagari passages are no longer merged into one independent source.
- **Vertical-slice coverage** (`backend/tests/test_api.py`): paragraph (`text`) and URL success paths, evidence-provenance/uncertainty assertions, and a prompt-injection boundary test (retrieved text is evidence, never instructions).
- **Privacy/log hygiene** (`backend/tests/test_logging_privacy.py`): submitted claim text is not written to logs, and validation errors do not echo user input.
- **Source-adapter reliability** (`backend/tests/test_source_adapters.py`, `test_analyzer.py`): OpenAlex/Wikidata/FactCheck success + soft-failure paths, FactCheck skips without a key, and one failing source does not block the others.
- **Error paths**: an NLI model-load failure degrades to `UNABLE_TO_ASSESS` with a visible degraded reason, and a URL-fetch failure returns typed `url_fetch_failed` (502).
- **Rate-limiter unit tests** (`test_limits.py`): per-client isolation and unprotected-path bypass, exercised directly on `RequestLimitsMiddleware`.
- **Limit/redirect edge cases**: a redirect loop beyond the hop limit is rejected (`url_extract`), and a streamed body with no `Content-Length` is capped while streaming (413).
- **Input validation**: out-of-range `options` and whitespace-only claims return typed 422; `docs/ARCHITECTURE.md` reconciled with the verified implementation (request limits, dense default, single-source safeguard).
- **SSRF hardening**: NAT64 (`64:ff9b::/96`, `64:ff9b:1::/48`) prefixes are now explicitly blocked (previously only incidentally, via `ipaddress.is_reserved`); `test_url_safety.py` covers IPv4 reserved/documentation ranges and the IPv4-mapped / IPv4-translated / 6to4 / teredo / NAT64 transition forms. `docs/SECURITY.md` updated.
- **Live smoke tests** (`backend/tests/test_live_smoke.py`): opt-in real-network tests for the Wikipedia adapter and the full `/api/analyze` pipeline; `live` is excluded from the default run so CI stays offline.
- **Phase 1 (partial)**: optional keyless **Wikinews** news source (`VERITY_ENABLE_WIKINEWS`, off by default) reusing the MediaWiki adapter; registry excludes it unless enabled.
- **Provenance/recency**: the report carries a publication-date limitation, and each claim notes how many of its evidence passages lack a date and therefore cannot be checked for recency.
- **Phase 2 (partial)**: deterministic rules-based claim-type classifier (`services/claim_type.py`); opinions/predictions/allegations/unclear return `NOT_VERIFIABLE` instead of a forced true/false verdict. Classifier accuracy is **not yet evaluated** (needs a labelled set).
- **Claim-type evaluation ready**: the held-out harness (`experiments/eval_e2e_heldout.py`) now scores predicted-vs-gold claim-type accuracy per type with a bootstrap CI, for when the labelled set exists.
- **Allegation handling**: allegations run the evidence pipeline but are always `NOT_VERIFIABLE`; the report discloses support/contradict counts and whether an *official-finding* signal appears, and never declares the allegation true or false (`services/allegation.py`).
- **Phase 3 (partial)**: tokenization is Unicode-aware; claim detection accepts Devanagari copulas/verbs **and** their Roman/Hinglish transliterations (`hai`, `tha`, `sthit`, ...), and the Devanagari danda (`।`) is a sentence boundary, so Hindi and Hinglish statements are extracted (and multi-sentence Hindi text is segmented) instead of being rejected or collapsed. Claim-type pre-classification and negation disclosure also recognise Hindi/Hinglish opinion/prediction/allegation markers, so non-fact Hindi/Hinglish statements route to `NOT_VERIFIABLE` instead of a forced verdict. **Language gate**: non-English input is detected (`looks_english`) and returned as `UNABLE_TO_ASSESS` with a disclosure rather than a possibly-wrong verdict; other Latin-script languages are not detected. Models remain English-first; Hindi quality is **unverified** (no labelled set).
- **Frontend integration test** (`backend/tests/test_frontend.py`): the served page exposes the expected UI contract, static assets load, and `app.js` calls `/api/analyze` and knows every backend status.
- **README capability status** table added (implemented / tested / evaluated / blocked).
- **Citation + injection checks**: every returned evidence URL is absolute http(s), and instructions embedded in fetched URL content do not change the verdict.

**Existing NLI result investigation:** saved model configs show different label orders and runtime reads config.id2label. The small model's saved confusion matrix is in canonical label order and consistent with its saved predictions, so its 0.448 accuracy is not explained by an obvious label mapping swap. Existing aggregate results cannot isolate the remaining cause.

**Open gate items:**
1. ~~Branch CI must pass after implementation.~~ **DONE** — the PR #1 merge left `main` red (ruff `UP041` + a url-safety test broken by the new `ge=1024` bound). Fixed in `d16ebe4`; CI run #10 on `d16ebe4` = **success**.
2. ~~Re-run retrieval on a larger deterministic distractor corpus and report paired BGE-minus-hybrid MRR bootstrap CI.~~ **DONE** — see "Harder-corpus retrieval" below.
3. Re-run both NLI candidates with bootstrap CIs; measure CPU latency and peak RAM. **PARTIAL** — base re-run: accuracy **0.675 [0.633, 0.716]**, macro-F1 **0.671 [0.630, 0.712]**, mean latency **159.9 ms/pair [155.6, 165.1]**. Small candidate **BLOCKED**: its DeBERTa-v2 tokenizer needs `sentencepiece`, whose DLL the host's Windows Application Control policy blocks; the historical 0.448/0.458 are not reproducible here.
4. Human-review and label at least 60 claims with a fixed held-out split, including opinions and allegations. **DRAFTED, AWAITING REVIEW** — `data/annotations/phase0_candidates.csv` (100 proposed rows; 62 held_out / 38 tuning) + `.md` notes. These are machine-proposed, not gold.
5. Tune tau_single only on a separate tuning split; the 8-claim diagnostic and Zorbax-9 regression are not held-out evidence. **PENDING** (blocked on item 4 sign-off).
6. Deployment remains blocked on owner-provided Hugging Face write credentials and authorization to create the Space. **BLOCKED.**

**Harder-corpus retrieval (recorded 2026-10-10).** Distractor pool caps at 2525 titles →
**2409 usable pages** (367 gold + 2042 distractors; 483 unavailable), 330 evaluable claims.
Bootstrap 95% CIs (2000 resamples). BGE dense: R@5 0.968 [0.952, 0.981], MRR **0.975 [0.961, 0.987]**.
Hybrid RRF: R@5 0.946 [0.923, 0.967], MRR 0.955 [0.935, 0.974]. Paired MRR difference
(BGE − hybrid) = **+0.0196, 95% CI [0.0027, 0.0377]** (n=330) — excludes zero. **Decision:** the
runtime default is now **dense-only** (`VERITY_RETRIEVAL_MODE=dense`, `backend/app/retrieval/pipeline.py`);
`hybrid` stays selectable. Full table in `docs/EVALUATION.md` and `docs/experiments/001-retrieval-comparison.md`.

**Next commands:** review `data/annotations/phase0_candidates.csv` and promote verified rows to
`phase0_e2e_template.csv` (keep >=60 held_out); then tune tau_single on the tuning split only. The
small NLI candidate can only be evaluated on a host where `sentencepiece` is not blocked.
