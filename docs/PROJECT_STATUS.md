# VerityAI Project Status

## Last Updated
2026-10-10 (Asia/Kolkata)

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
  verified green on GitHub** (run `38047977416` on `f97a075` ⇒ success; run #1 on `47a7602` ⇒
  success).
- **M7 (part)** — **GitHub publication**: public repo at
  [`github.com/ADxSD-143/VerityAI`](https://github.com/ADxSD-143/VerityAI), `main` = `eec56f7`.
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
| `pytest -q` (76 tests) | exit code 0, all passed |
| `pytest -q -m live` | not automated (opt-in); sources exercised via `/api/analyze`, `eval_e2e`, and a live Zorbax-9 re-check |
| `POST /api/analyze` (live) | 200, real multi-source evidence |
| `POST /api/analyze-url` (metadata IP) | 400 `unsafe_url` |
| secret scan (grep + `git ls-files`) | clean; no `.env`; no tracked file > 1 MB |
| GitHub Actions CI (run `38050601549`, `eec56f7`) | **success** |
| `docker build` | **not run** — Docker is not installed on this host |

## Evaluation
All artefacts in `experiments/results/`:
- `fever_sample.json` — 500 claims, seed 42, labels 166 REFUTES / 167 SUPPORTS / 167 NEI; 367 gold
  pages + 800 distractors.
- `eval_retrieval.json` — 330 evaluable claims, 1161-page corpus. R@5/MRR: TF-IDF 0.958/0.941,
  BM25 0.943/0.901, BGE 0.973/0.985, hybrid 0.953/0.960, hybrid+rerank 0.971/0.982.
- `eval_nli.json` (base) — accuracy 0.675, macro-F1 0.671, 90.5 ms/pair.
- `eval_nli_small.json` (small) — accuracy 0.448, macro-F1 0.458, 98.0 ms/pair.
- `eval_e2e.json` — 4/8 live claims matched (original run; unchanged). **Live re-check (single
  observation)** of the one false positive after adding the safeguard: Zorbax-9 →
  `INSUFFICIENT_EVIDENCE` (best entailment 0.519 < `tau_single` 0.75).
- `measure_resources.json` — BGE 134.5 MB, NLI 380.0 MB, reranker 91.8 MB (all < 500 MB budget).

## Decisions
- Default retrieval = hybrid BM25+BGE (RRF). BGE dense measured higher MRR; hybrid retained for
  exact-term robustness — a documented judgement call, not a measured win. Reranker **off** by
  default.
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
default branch `main`, `eec56f7` on `main`, CI green.

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

**Existing NLI result investigation:** saved model configs show different label orders and runtime reads config.id2label. The small model's saved confusion matrix is in canonical label order and consistent with its saved predictions, so its 0.448 accuracy is not explained by an obvious label mapping swap. Existing aggregate results cannot isolate the remaining cause.

**Open gate items:**
1. Branch CI must pass after implementation.
2. Re-run retrieval on a larger deterministic distractor corpus and report paired BGE-minus-hybrid MRR bootstrap CI.
3. Re-run both NLI candidates with bootstrap CIs; measure CPU latency and peak RAM on the target host.
4. Human-review and label at least 60 claims with a fixed held-out split, including opinions and allegations.
5. Tune tau_single only on a separate tuning split; the 8-claim diagnostic and Zorbax-9 regression are not held-out evidence.
6. Deployment remains blocked on owner-provided Hugging Face write credentials and authorization to create the Space.

**Next commands after CI passes:** run the FEVER sample builder with 4,000 distractor pages, then retrieval evaluation with max-pages 5000; rerun both NLI commands in docs/EVALUATION.md; complete data/annotations/phase0_e2e_template.csv with human-reviewed labels before computing held-out metrics.
