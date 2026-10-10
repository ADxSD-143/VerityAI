"""FastAPI application factory.

Serves the JSON API under ``/api`` (plus ``/health``) and mounts the static,
build-free frontend at ``/``. Errors are translated to a stable JSON shape without
leaking tracebacks, local paths or secrets.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api.routes import router
from .config import get_settings
from .core.errors import VerityError
from .schemas.models import ErrorResponse
from .services.analyzer import Analyzer

logger = logging.getLogger("verityai")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def _clean_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for error in errors:
        entry = dict(error)
        ctx = entry.get("ctx")
        if isinstance(ctx, dict):
            entry["ctx"] = {k: str(v) for k, v in ctx.items()}
        entry.pop("input", None)
        cleaned.append(entry)
    return cleaned


def create_app() -> FastAPI:
    settings = get_settings()
    analyzer = Analyzer(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.started_at = time.time()
        if settings.verity_preload_models:
            try:
                threading.Thread(target=analyzer.preload, daemon=True).start()
            except Exception:  # noqa: BLE001 - warm-up is strictly best-effort
                logger.warning("model preload could not be started", exc_info=False)
        yield

    app = FastAPI(
        title="VerityAI",
        version=__version__,
        description="Evidence-grounded, multi-source AI fact-checking platform.",
        lifespan=lifespan,
    )
    app.state.analyzer = analyzer
    app.state.started_at = time.time()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.exception_handler(VerityError)
    async def _verity_handler(_: Request, exc: VerityError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=ErrorResponse(error=exc.message, code=exc.code, details=exc.details).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Request validation failed.",
                code="invalid_input",
                details={"errors": _clean_validation_errors(exc.errors())},
            ).model_dump(),
        )

    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
