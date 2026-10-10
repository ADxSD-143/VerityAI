# VerityAI Project Status

## Last Updated
2026-10-10 14:30 +05:30 (Asia/Kolkata)

## Current Milestone
M2 — Pretrained semantic retrieval (M0, M1 PASS). M2/M3 code exists; measured benchmark
results come from the M4 scripts.

## Overall Status
In progress.

## Environment
- **OS**: Windows (win32), PowerShell 5.1, working dir `D:\project ideas\VerityAI`.
- **Python**: 3.11.7 (`C:\Users\LENOVO\AppData\Local\Programs\Python\Python311\python.exe`).
  The `py` launcher is **broken** (points at a missing Python 3.14) — use `python` / the venv.
- **Venv**: `.venv` (on D:). Deps installed from the **Tsinghua PyPI mirror** (PyPI's CDN was
  ~33 KB/s here vs ~245 KB/s from the mirror).
- **Node**: v24.15.0 / npm 11.12.1 (unused — vanilla frontend).
- **git**: 2.55.0. Identity `aditya narayan <adityanarayansd@gmail.com>`. Repo initialised
  (branch `main`, first commit `ca099f3`).
- **GitHub CLI**: **NOT installed** (`gh` absent) → M7 repo creation blocked pending install/auth.
- **Hugging Face auth**: **no token** present → M7 Space deploy blocked pending auth.
- **Compute**: i7-12650HX (14c/20t), 15.73 GB RAM, RTX 4050 4 GB (unused; CPU default).
  Disk: C: 29.5 GB free (tight), D: 213 GB free → venv, `HF_HOME=D:\hf-cache`, embed cache on D:.
- **Selected hosting**: Hugging Face Spaces (Docker), app port 7860.

### Environment blocker found and fixed: Windows Application Control
A Windows Application Control policy blocked the **newest** wheels of `scikit-learn` (1.9.1),
`pandas` (3.0.6) and `pyarrow` (26.0.0) with *"DLL load failed ... blocked by an Application
Control policy"*. Because `transformers` imports `sklearn` when it is present, this broke
`transformers` → `sentence-transformers` entirely.

**Fix**: pin older, allowed releases — `scikit-learn==1.5.2`, `pandas==2.2.3`, `pyarrow==17.0.0`
(constraints added to `pyproject.toml` `[eval]`). All imports now succeed:
`torch 2.14.1+cpu`, `transformers 4.57.6`, `sentence-transformers 3.4.1`, `numpy 2.4.6`,
`datasets 2.21.0`.

## Completed
- **M0** — environment audit; `AGENTS.md`, `PLAN.md`, `docs/PROJECT_STATUS.md`.
- **M1** — verified end-to-end:
  - `pytest -q` → **63 passed**; `ruff check backend experiments scripts` → **All checks passed**.
  - Server started; `GET /health` → `{"status":"ok", ... models loaded: BGE + NLI}`.
  - `POST /api/analyze` for *"The Eiffel Tower is located in Paris."* → real evidence
    (wikipedia n=36, wikidata n=14, openalex n=38; factcheck `skipped`), 11 629 ms, not degraded,
    verdict `CONFLICTING_EVIDENCE` (5 supporting / 1 contradicting passage).
  - Frontend `/`, `/styles.css`, `/app.js` → 200. `analyze-url` with `169.254.169.254` → 400
    `unsafe_url`. Empty body → 422.
- Models downloaded to `D:\hf-cache` (490.7 MB cached): BGE load 72.1 s, NLI load 112.7 s
  (both include download).

## In Progress
- M2/M3 gate evidence: run the retrieval benchmark, NLI benchmark and resource measurement.

## Next Actions
1. `python experiments/build_fever_sample.py --limit 500 --seed 42` (FEVER dev sample).
2. `python experiments/eval_retrieval.py` and `python experiments/eval_nli.py`.
3. `python experiments/eval_e2e.py`; `python experiments/measure_resources.py`.
4. Fill the recorded results into `docs/EVALUATION.md`, `README.md` and `docs/experiments/`.
5. Commit; then M6 docs/CI polish; then M7 publish/deploy.

## Milestone Gates
- M0: **PASS** · M1: **PASS** · M2–M7: NOT RUN.

## Tests and Verification
| Command | Outcome |
|---|---|
| `ruff check backend experiments scripts` | All checks passed |
| `pytest -q` | 63 passed (1 Starlette deprecation warning) |
| `uvicorn app.main:app` + `GET /health` | 200, models loaded |
| `POST /api/analyze` (Eiffel Tower) | 200, real multi-source evidence, 11.6 s |
| `GET /`, `/styles.css`, `/app.js` | 200 |
| `POST /api/analyze-url` (metadata IP) | 400 `unsafe_url` |
| `POST /api/analyze` `{}` | 422 `invalid_input` |

## Evaluation
Not yet run (M4). No metrics recorded. `experiments/results/` is empty.

## Decisions
- Vanilla no-build frontend; HF Spaces Docker hosting; CPU-only torch.
- Deterministic regex sentence segmentation + entity hints (no spaCy dependency).
- `VERITY_PRELOAD_MODELS` switch so tests never download models.
- Pinned older sklearn/pandas/pyarrow for Windows Application Control compatibility (see above).
- `.commandcode/` gitignored; `.gitattributes` normalises to LF.

## Blockers
1. **`gh` CLI not installed** — blocks `gh repo create` in M7. Action: install (`winget install
   --id GitHub.cli`) and authenticate, or push via an existing credential. Independent work continues.
2. **No Hugging Face token** — blocks automated Space deploy in M7. Action: `huggingface-cli login`
   or set `HF_TOKEN`. Deploy artifacts are prepared meanwhile.

## GitHub
Local repo initialised, `main`, commit `ca099f3`. Not published yet. Intended: public `VerityAI`.

## Deployment
Not deployed. Intended: Hugging Face Spaces (Docker), port 7860. `Dockerfile` + README Spaces
frontmatter are in place.

## Resume Instructions
Continue M2/M3: run the FEVER sample build and the evaluation scripts (see Next Actions), then fill
the results into `docs/EVALUATION.md`. Do not re-run the environment audit or re-create control
files. The two M7 blockers must not halt M2–M6. Note: the server was stopped after verification;
restart with `HF_HOME=D:\hf-cache .\.venv\Scripts\python.exe -m uvicorn app.main:app`.
