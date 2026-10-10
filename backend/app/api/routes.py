"""API routes: health, analyze, analyze-url."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from .. import __version__
from ..models_io import device, loaded_models
from ..schemas.models import (
    AnalysisReport,
    AnalyzeRequest,
    AnalyzeUrlRequest,
    HealthResponse,
)
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


@router.post("/api/analyze", response_model=AnalysisReport, tags=["analysis"])
async def analyze(payload: AnalyzeRequest, request: Request) -> AnalysisReport:
    return await request.app.state.analyzer.analyze(payload)


@router.post("/api/analyze-url", response_model=AnalysisReport, tags=["analysis"])
async def analyze_url(payload: AnalyzeUrlRequest, request: Request) -> AnalysisReport:
    request_model = AnalyzeRequest(url=payload.url, options=payload.options)
    return await request.app.state.analyzer.analyze(request_model)
