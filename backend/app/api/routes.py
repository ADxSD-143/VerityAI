"""API routes: health, analyze, analyze-url."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Request

from .. import __version__
from ..core.errors import AnalysisTimeoutError
from ..models_io import device, loaded_models
from ..schemas.models import AnalysisReport, AnalyzeRequest, AnalyzeUrlRequest, HealthResponse
from ..sources.base import now_iso

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(request: Request) -> HealthResponse:
    started = getattr(request.app.state, "started_at", time.time())
    return HealthResponse(
        status="ok",
        version=__version__,
        device=device(),
        models_loaded=loaded_models(),
        uptime_s=round(time.time() - started, 1),
        timestamp=now_iso(),
    )


async def _analyze_with_timeout(request: Request, payload: AnalyzeRequest) -> AnalysisReport:
    timeout_s = request.app.state.settings.verity_analysis_timeout_s
    try:
        return await asyncio.wait_for(request.app.state.analyzer.analyze(payload), timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        raise AnalysisTimeoutError(
            "Analysis exceeded the configured time limit.", details={"timeout_s": timeout_s}
        ) from exc


@router.post("/api/analyze", response_model=AnalysisReport, tags=["analysis"])
async def analyze(payload: AnalyzeRequest, request: Request) -> AnalysisReport:
    return await _analyze_with_timeout(request, payload)


@router.post("/api/analyze-url", response_model=AnalysisReport, tags=["analysis"])
async def analyze_url(payload: AnalyzeUrlRequest, request: Request) -> AnalysisReport:
    return await _analyze_with_timeout(
        request, AnalyzeRequest(url=payload.url, options=payload.options)
    )
