# VerityAI Project Status

## Last Updated
2026-10-10 15:55 +05:30 (Asia/Kolkata)

## Current Milestone
M5/M6 (M0–M4 PASS). M7 publication/deployment is prepared but blocked on credentials.

## Overall Status
In progress — the application is built, tested and evaluated; publishing/deploying is blocked on
GitHub CLI install + Hugging Face auth.

## Environment
- **OS**: Windows (win32), PowerShell 5.1, repo `D:\project ideas\VerityAI`.
- **Python**: 3.11.7 in `.venv` (deps installed from a PyPI **mirror**; PyPI's CDN was ~33 KB/s here).
- **Key versions**: `torch 2.14.1+cpu`, `transformers 4.57.6`, `sentence-transformers 3.4.1`,
  `numpy 2.4.6`, `scikit-learn 1.5.2`, `pandas 2.2.3`, `pyarrow 17.0.0`, `datasets 2.21.0`.
- **Node**: v24.15.0 (unused — vanilla frontend). **git**: 2.55.0.
- **GitHub CLI**: NOT installed. **Hugging Face auth**: no token. **Docker**: NOT installed.
- **Compute**: i7-12650HX (14c/20t), 15.73 GB RAM, CPU-only inference. `HF_HOME=D:\hf-cache`.

## Completed
- **M0** audit + control files.
- **M1** — app verified end-to-end (63 tests pass, ruff clean, live `/api/analyze` with real
  Wikipedia + Wikidata + OpenAlex evidence, SSRF + validation paths).
- **M2** — BGE dense + BM25 + RRF + dedup + optional reranker implemented; **retrieval benchmark
  run** (330 evaluable claims, 1161-page corpus).
- **M3** — NLI implemented with config-read label map; **NLI benchmark run** for base and small.
- **M4** — FEVER `labelled_dev` sample (500, seed 42), all evaluation artefacts saved.
- **M5** (code) — SSRF-safe URL extraction + tests; secret scan clean (no `.env`, no secret-named
  files, no tracked file > 1 MB).
- **M6** (code/docs) — `README.md`, `AGENTS.md`, `PLAN.md`, `ARCHITECTURE`, `API`, `SECURITY`,
  `DATASETS`, `EVALUATION`, `DEVELOPMENT_LOG`, 11 theory pages, 4 experiment records, CI workflow,
  Dockerfile, README Spaces frontmatter.

## In Progress
- M5/M6 gate sign-off (docs + CI are written; CI has not run on GitHub yet because the repo is not
  published).
- M7 publication/deployment.

## Next Actions
1. Install and authenticate the GitHub CLI (`winget install --id GitHub.cli`), then create the
   public repo and push.
2. Authenticate Hugging Face (`huggingface-cli login` or `HF_TOKEN`), then create the Docker Space.
3. After deploy: verify the public frontend + `/health` + one real analysis, and replace the
   `DEPLOY_URL` placeholder in `README.md`.
4. Run CI on GitHub and confirm it is green.

## Milestone Gates
- M0 **PASS** · M1 **PASS** · M2 **PASS** · M3 **PASS** · M4 **PASS** · M5/M6 code+docs complete
  (gate sign-off pending a published CI run) · M7 **BLOCKED** on credentials.

## Tests and Verification
| Command | Outcome |
|---|---|
| `ruff check backend experiments scripts` | All checks passed |
| `pytest -q` (63 tests) | exit code 0, all passed |
| `pytest -q -m live` | not yet run (opt-in; sources already exercised via `/api/analyze` and `eval_e2e`) |
| `POST /api/analyze` (live) | 200, real multi-source evidence, 11.6 s |
| `POST /api/analyze-url` (metadata IP) | 400 `unsafe_url` |
| secret scan (grep + `git ls-files`) | clean; no `.env`; no tracked file > 1 MB |
| `docker build` | **not run** — Docker is not installed on this host |

## Evaluation
All artefacts in `experiments/results/`:
- `fever_sample.json` — 500 claims, seed 42, labels 166 REFUTES / 167 SUPPORTS / 167 NEI; 367 gold
  pages + 800 distractors.
- `eval_retrieval.json` — 330 evaluable claims, 1161-page corpus. R@5/MRR: TF-IDF 0.958/0.941,
  BM25 0.943/0.901, BGE 0.973/0.985, hybrid 0.953/0.960, hybrid+rerank 0.971/0.982.
- `eval_nli.json` (base) — accuracy 0.675, macro-F1 0.671, 90.5 ms/pair.
- `eval_nli_small.json` (small) — accuracy 0.448, macro-F1 0.458, 98.0 ms/pair.
- `eval_e2e.json` — 4/8 live claims matched; one false positive on a nonsense claim documented.
- `measure_resources.json` — BGE 134.5 MB, NLI 380.0 MB, reranker 91.8 MB (all < 500 MB budget).

## Decisions
- Default retrieval = hybrid BM25+BGE (RRF). BGE dense measured higher MRR; hybrid retained for
  exact-term robustness — a documented judgement call, not a measured win. Reranker **off** by
  default (no ranking gain for +1.5 s/claim).
- Default NLI = base model (clearly better than the small model on this host).
- Aggregation policy **not** tuned on the 8-claim e2e set; the single-source false positive is
  documented as a limitation rather than patched to fit the test.
- Pinned older sklearn/pandas/pyarrow for Windows Application Control compatibility.

## Blockers
1. **`gh` CLI not installed** — blocks repo creation/push. Action: `winget install --id GitHub.cli`
   then `gh auth login`, or push with an existing credential.
2. **No Hugging Face token** — blocks Space creation/upload. Action: `huggingface-cli login` or set
   `HF_TOKEN`.
3. **Docker not installed** — the image cannot be built locally; HF Spaces builds it server-side.
   Action: install Docker Desktop if local build validation is wanted.
All independent work (code, tests, evaluation, docs, deploy artefacts) is complete.

## GitHub
Local repo on `main`. Intent: public `VerityAI` under the authenticated account. **Not published.**

## Deployment
Not deployed. `Dockerfile` + README Spaces frontmatter are ready (port 7860). Public URL to be
recorded here and in `README.md` once verified.

## Resume Instructions
Everything up to publishing is done. To finish M7: install/authenticate `gh` and HF, push the repo,
create the Docker Space, then verify the public frontend, `/health`, and one real analysis and write
the URL into `README.md` (`DEPLOY_URL` block). Do not re-run the environment audit, the evaluation
runs, or re-create the control files. Restart the server with:
`$env:HF_HOME="D:\hf-cache"; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`.
