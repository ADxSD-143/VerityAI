"""Pydantic v2 request/response contracts for the VerityAI API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Verdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    UNABLE_TO_ASSESS = "UNABLE_TO_ASSESS"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"


class NLIProbabilities(BaseModel):
    entailment: float
    neutral: float
    contradiction: float


class EvidenceItem(BaseModel):
    passage: str
    source: str
    title: str
    url: str
    publisher: str
    published_at: str | None = None
    retrieved_at: str
    rank: int | None = None
    retrieval_score: float | None = None
    bm25_rank: int | None = None
    dense_rank: int | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None
    nli_label: str | None = None
    nli_score: float | None = None
    nli_probs: NLIProbabilities | None = None
    independent_group: int | None = None
    note: str | None = None


class FactCheckItem(BaseModel):
    claim_reviewed: str | None = None
    publisher: str
    publisher_verdict: str
    url: str
    reviewed_at: str | None = None
    retrieved_at: str
    source: str = "factcheck"


class ClaimStats(BaseModel):
    passages_considered: int
    support_passages: int
    contradict_passages: int
    support_sources: int
    contradict_sources: int
    independent_groups: int


class ClaimAssessment(BaseModel):
    claim_id: str
    text: str
    start: int | None = None
    end: int | None = None
    status: Verdict
    claim_type: str | None = None
    explanation: str
    limited_corroboration: bool = False
    claim_notes: list[str] = Field(default_factory=list)
    stats: ClaimStats
    supporting: list[EvidenceItem] = Field(default_factory=list)
    contradicting: list[EvidenceItem] = Field(default_factory=list)
    neutral: list[EvidenceItem] = Field(default_factory=list)
    fact_checks: list[FactCheckItem] = Field(default_factory=list)


class SourceRecord(BaseModel):
    source: str
    endpoint: str | None = None
    queries: list[str] = Field(default_factory=list)
    status: str
    n_results: int = 0
    error: str | None = None


class InputInfo(BaseModel):
    kind: str
    value_preview: str
    url: str | None = None
    title: str | None = None
    characters: int


class ModelInfo(BaseModel):
    name: str
    model_id: str
    revision: str | None = None
    role: str
    device: str
    loaded: bool


class AnalysisMeta(BaseModel):
    analysis_id: str
    created_at: str
    processing_ms: int
    degraded_mode: bool = False
    degraded_reasons: list[str] = Field(default_factory=list)
    models: list[ModelInfo] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    input: InputInfo
    claims: list[ClaimAssessment]
    sources_queried: list[SourceRecord] = Field(default_factory=list)
    source_failures: list[SourceRecord] = Field(default_factory=list)
    meta: AnalysisMeta


class AnalyzeOptions(BaseModel):
    max_claims: int | None = Field(default=None, ge=1, le=20)
    top_k_retrieval: int | None = Field(default=None, ge=1, le=100)
    top_k_nli: int | None = Field(default=None, ge=1, le=50)
    use_reranker: bool | None = None


class AnalyzeRequest(BaseModel):
    claim: str | None = None
    text: str | None = None
    url: str | None = None
    options: AnalyzeOptions | None = None

    @model_validator(mode="after")
    def _exactly_one_input(self) -> AnalyzeRequest:
        provided = [
            bool(self.claim and self.claim.strip()),
            bool(self.text and self.text.strip()),
            bool(self.url and self.url.strip()),
        ]
        if sum(provided) != 1:
            raise ValueError("Provide exactly one of 'claim', 'text', or 'url'.")
        return self


class AnalyzeUrlRequest(BaseModel):
    url: str
    options: AnalyzeOptions | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    device: str
    models_loaded: list[str]
    uptime_s: float
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)
