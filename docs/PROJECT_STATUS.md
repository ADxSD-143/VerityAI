# VerityAI Project Status

## Last Updated
2026-10-10 13:06 +05:30 (Asia/Kolkata)

## Current Milestone
M1 — Application skeleton and real evidence retrieval (M0 PASS).

## Overall Status
In progress.

## Environment
- **OS**: Windows (win32), PowerShell 5.1, working dir `D:\project ideas\VerityAI`.
- **Python**: 3.11.7 at `C:\Users\LENOVO\AppData\Local\Programs\Python\Python311\python.exe`.
  - `py` launcher is **broken** (points at a non-existent `C:\Program Files\Python314`) — use
    `python` / the venv interpreter directly.
- **pip**: 23.2.1 (upgraded inside venv).
- **Node**: v24.15.0, npm 11.12.1 (not required — vanilla frontend, no build step).
- **git**: 2.55.0.windows.5. Identity: `aditya narayan <adityanarayansd@gmail.com>`.
- **GitHub CLI**: **NOT installed** (`gh` not on PATH, no CLI config). Winget is available.
- **Hugging Face auth**: **no token found** (`~/.cache/huggingface/token` absent, `HF_TOKEN`
  unset, `HUGGINGFACE_HUB_TOKEN` unset).
- **Compute**: Intel i7-12650HX, 14 cores / 20 threads. RAM 15.73 GB.
  GPU: NVIDIA GeForce RTX 4050 Laptop 4 GB (optional; CPU is the default target).
- **Disk**: C: 29.5 GB free (tight), D: 213.2 GB free → venv + HF cache live on D:.
- **Network**: huggingface.co HTTP 200, pypi.org HTTP 200.
- **Pre-existing global libs (not used by the venv)**: fastapi 0.141.1, httpx 0.28.1,
  numpy 2.4.3, pydantic 2.13.4, scikit-learn 1.8.0, uvicorn 0.52.1, requests 2.34.2.
  No torch / transformers / sentence-transformers installed.
- **Selected hosting**: Hugging Face Spaces (Docker SDK), free CPU tier.
- **Venv**: `.venv` (Python 3.11.7), created at repo root on D:. `HF_HOME` should be set to a
  D: path (e.g. `D:\hf-cache`) to avoid filling C:.

## Completed
- M0 environment audit (above).
- Repo scaffold: `pyproject.toml`, `.gitignore`, `LICENSE` (MIT), `.env.example`,
  `AGENTS.md`, `PLAN.md`, `docs/PROJECT_STATUS.md`.
- Dependency install started in the background (task `s0m284gz`).

## In Progress
- M1: FastAPI skeleton, MediaWiki adapter, static frontend, validation, tests.

## Next Actions
1. Write `backend/app` package: config, schemas, core text utils, sources (MediaWiki),
   retrieval skeleton, services (claim extraction, analyzer), `main.py`.
2. Write `frontend/` (index.html, styles.css, app.js).
3. Write tests; run `pytest -q` once the install finishes.
4. Start the server and verify `/health` + a real `POST /api/analyze`.

## Milestone Gates
- M0: **PASS** (audit completed; plan executable; no paid service required; model
  verification plan recorded in `PLAN.md` and the build plan).
- M1–M7: NOT RUN.

## Tests and Verification
| Command | Outcome |
|---|---|
| `python --version` | Python 3.11.7 |
| `node --version` | v24.15.0 |
| `git --version` | 2.55.0.windows.5 |
| `gh --version` | **not installed** (CommandNotFoundException) |
| `Invoke-WebRequest huggingface.co` (HEAD) | 200 |
| `Invoke-WebRequest pypi.org` (HEAD) | 200 |

## Evaluation
Not started (M4). No metrics recorded yet.

## Decisions
- Vanilla no-build frontend (user-approved) — simplest, lowest-risk deploy.
- Hugging Face Spaces Docker hosting (user-approved).
- Deterministic regex sentence segmentation + regex entity/number/date hints instead of
  spaCy, to cut install/deploy risk and keep the pipeline dependency-light. Rationale: the
  spec lists spaCy as optional ("where useful"); a custom splitter is deterministic and
  fully testable. Documented in `docs/ARCHITECTURE.md`.
- CPU-only torch wheels (matches the free host; portable and reproducible).

## Blockers
1. **`gh` CLI not installed** — blocks the `gh repo create ... --push` workflow in M7.
   Evidence: `gh : The term 'gh' is not recognized`. Action: attempt a non-interactive
   `winget install --id GitHub.cli`; otherwise the user must install gh and authenticate, or
   provide a way to push. Independent work (build, tests, eval, Dockerfile) continues.
2. **No Hugging Face token** — blocks automated Space creation/upload in M7.
   Evidence: token file absent, env vars unset. Action: user must authenticate
   (`huggingface-cli login` or set `HF_TOKEN`). All deploy artifacts are prepared meanwhile.

## GitHub
Not created yet. Intended: public `VerityAI` under the authenticated account.

## Deployment
Not deployed. Intended: Hugging Face Spaces (Docker), app port 7860.

## Resume Instructions
Continue M1: create the `backend/app` package and frontend, then run `pytest -q` (after the
background install `s0m284gz` completes) and start the server to verify `/health` and a live
`POST /api/analyze`. Do **not** re-run the environment audit. Do **not** re-create the control
files. The two blockers above are M7-only and must not halt M1–M6.
