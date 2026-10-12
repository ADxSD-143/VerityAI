"""End-to-end analysis orchestration.

Request flow:
  validate -> (URL fetch) -> claim extraction -> concurrent source retrieval
  -> hybrid retrieval -> NLI on the top candidates -> independence clustering
  -> conservative aggregation -> structured, traceable report.

If a model or source fails, the failure is surfaced (``degraded_mode`` / source
records) and no evidence, score or citation is fabricated.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import httpx

from ..analysis.aggregation import AggregateInput, AggregateResult, aggregate
from ..analysis.independence import cluster_passages, document_key
from ..analysis.nli import NLIModel, NLIScore
from ..config import Settings, get_settings
from ..core.errors import ModelLoadError
from ..core.text import looks_english, normalize_whitespace
from ..models_io import device, loaded_models
from ..retrieval.pipeline import RankedPassage, default_embedding_cache, retrieve
from ..schemas.models import (
    AnalysisMeta,
    AnalysisReport,
    AnalyzeRequest,
    ClaimAssessment,
    ClaimStats,
    EvidenceItem,
    FactCheckItem,
    InputInfo,
    ModelInfo,
    NLIProbabilities,
    SourceRecord,
    Verdict,
)
from ..sources.base import EvidencePassage, SourceResult, now_iso
from ..sources.registry import build_adapters
from .allegation import summarize_allegation
from .claim_extraction import ExtractedClaim, extract_claims, query_variants, single_claim
from .claim_type import (
    ALLEGATION,
    NO_SEARCH_TYPES,
    OPINION_SUBJECTIVE,
    PREDICTION,
    UNCLEAR,
    classify_claim_type,
)
from .url_extract import fetch_and_extract

MAX_PASSAGES_PER_CLAIM = 400
PREVIEW_CHARS = 240

STATIC_LIMITATIONS = [
    "Retrieval covers only the permitted sources listed in this response; it is not a "
    "search of the entire internet.",
    "NLI scores describe a specific evidence-claim pair and are not the probability that "
    "the claim is true.",
    "Evidence reflects each source's text at retrieval time and may differ from how it "
    "reads now.",
    "Publication dates are shown only when a source provides them; a passage with no date "
    "cannot be checked for recency, and dated evidence may still be outdated.",
    "Publisher fact-check verdicts are shown separately and are never treated as ground truth.",
]


def _preview(text: str) -> str:
    cleaned = normalize_whitespace(text)
    return cleaned[:PREVIEW_CHARS] + ("..." if len(cleaned) > PREVIEW_CHARS else "")


class Analyzer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.adapters = build_adapters(self.settings)
        self._cache = default_embedding_cache()
        self._nli: NLIModel | None = None

    def _nli_model(self) -> NLIModel:
        if self._nli is None:
            self._nli = NLIModel(
                self.settings.verity_nli_model_id, self.settings.verity_nli_model_revision
            )
        return self._nli

    def preload(self) -> None:
        """Best-effort warm-up of the dense and NLI models (used at startup)."""
        from ..models_io import get_sentence_transformer

        get_sentence_transformer(
            self.settings.verity_bge_model_id, self.settings.verity_bge_model_revision
        )
        self._nli_model()

    async def analyze(self, request: AnalyzeRequest) -> AnalysisReport:
        started = time.perf_counter()
        options = request.options
        max_claims = (options.max_claims if options and options.max_claims else None) or (
            self.settings.verity_max_claims
        )
        top_k = (options.top_k_retrieval if options and options.top_k_retrieval else None) or (
            self.settings.verity_top_k_retrieval
        )
        top_k_nli = (options.top_k_nli if options and options.top_k_nli else None) or (
            self.settings.verity_top_k_nli
        )
        use_reranker = (
            options.use_reranker
            if options and options.use_reranker is not None
            else self.settings.verity_use_reranker
        )

        claims, input_info = await self._resolve_input(request, max_claims)

        degraded_reasons: list[str] = []
        claims_out: list[ClaimAssessment] = []
        source_records: list[SourceRecord] = []
        failures: list[SourceRecord] = []

        timeout = httpx.Timeout(self.settings.verity_source_timeout_s)
        headers = {"User-Agent": self.settings.verity_user_agent}
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for index, claim in enumerate(claims):
                claim_type = classify_claim_type(claim.text)
                if claim_type in NO_SEARCH_TYPES:
                    claims_out.append(self._non_verifiable(claim, index, claim_type))
                    continue
                if not looks_english(claim.text):
                    claims_out.append(self._unsupported_language(claim, index, claim_type))
                    continue
                assessment, reasons, records, failed = await self._analyze_claim(
                    claim,
                    index,
                    client,
                    top_k=top_k,
                    top_k_nli=top_k_nli,
                    use_reranker=use_reranker,
                )
                assessment.claim_type = claim_type
                if claim_type == ALLEGATION:
                    assessment = self._apply_allegation_policy(assessment)
                claims_out.append(assessment)
                degraded_reasons.extend(reasons)
                source_records.extend(records)
                failures.extend(failed)

        processing_ms = int((time.perf_counter() - started) * 1000)
        if not claims_out:
            claims_out = []
        return AnalysisReport(
            input=input_info,
            claims=claims_out,
            sources_queried=source_records,
            source_failures=failures,
            meta=AnalysisMeta(
                analysis_id=uuid.uuid4().hex[:12],
                created_at=now_iso(),
                processing_ms=processing_ms,
                degraded_mode=bool(degraded_reasons),
                degraded_reasons=sorted(set(degraded_reasons)),
                models=self._model_infos(use_reranker),
                limitations=STATIC_LIMITATIONS,
            ),
        )

    async def _resolve_input(
        self, request: AnalyzeRequest, max_claims: int
    ) -> tuple[list[ExtractedClaim], InputInfo]:
        if request.url:
            article = await fetch_and_extract(request.url, self.settings)
            claims = extract_claims(article.text, max_claims=max_claims)
            return claims, InputInfo(
                kind="url",
                value_preview=_preview(article.text),
                url=article.url,
                title=article.title,
                characters=len(article.text),
            )
        if request.text:
            claims = extract_claims(request.text, max_claims=max_claims)
            return claims, InputInfo(
                kind="text", value_preview=_preview(request.text), characters=len(request.text)
            )
        claims = single_claim(request.claim or "")
        return claims, InputInfo(
            kind="claim",
            value_preview=_preview(request.claim or ""),
            characters=len(request.claim or ""),
        )

    async def _analyze_claim(
        self,
        claim: ExtractedClaim,
        index: int,
        client: httpx.AsyncClient,
        *,
        top_k: int,
        top_k_nli: int,
        use_reranker: bool,
    ) -> tuple[ClaimAssessment, list[str], list[SourceRecord], list[SourceRecord]]:
        degraded: list[str] = []
        variants = query_variants(claim.text)

        results = await asyncio.gather(
            *[adapter.search(claim.text, variants, client) for adapter in self.adapters],
            return_exceptions=True,
        )

        passages: list[EvidencePassage] = []
        fact_checks: list[FactCheckItem] = []
        records: list[SourceRecord] = []
        failures: list[SourceRecord] = []
        for adapter, result in zip(self.adapters, results, strict=True):
            if isinstance(result, BaseException):
                record = SourceRecord(
                    source=adapter.name, endpoint=adapter.endpoint, queries=variants,
                    status="error", n_results=0, error=str(result),
                )
                records.append(record)
                failures.append(record)
                continue
            assert isinstance(result, SourceResult)
            record = SourceRecord(
                source=adapter.name, endpoint=result.endpoint or adapter.endpoint,
                queries=result.queries or variants, status=result.status,
                n_results=result.n_results, error=result.error,
            )
            records.append(record)
            if result.status == "error":
                failures.append(record)
            passages.extend(result.passages[:MAX_PASSAGES_PER_CLAIM])
            if result.fact_checks:
                fact_checks.extend(
                    FactCheckItem(
                        claim_reviewed=fc.claim_reviewed, publisher=fc.publisher,
                        publisher_verdict=fc.publisher_verdict, url=fc.url,
                        reviewed_at=fc.reviewed_at, retrieved_at=fc.retrieved_at,
                        source=fc.source,
                    )
                    for fc in result.fact_checks
                )

        passages = passages[:MAX_PASSAGES_PER_CLAIM]

        outcome = await asyncio.to_thread(
            retrieve, claim.text, passages, top_k=top_k, use_reranker=use_reranker, cache=self._cache
        )
        degraded.extend(outcome.degraded_reasons)

        analyzed: list[RankedPassage] = outcome.ranked[:top_k_nli]
        scores: list[NLIScore] = []
        if analyzed:
            pairs = [(rp.passage.text, claim.text) for rp in analyzed]
            try:
                scores = await asyncio.to_thread(self._nli_model().predict_batch, pairs)
            except ModelLoadError as exc:
                degraded.append(f"evidence assessment unavailable: {exc}")
                scores = []

        groups = (
            cluster_passages([rp.passage.text for rp in analyzed],
                             [document_key(rp.passage) for rp in analyzed])
            if analyzed
            else []
        )

        supporting: list[EvidenceItem] = []
        contradicting: list[EvidenceItem] = []
        neutral: list[EvidenceItem] = []
        agg_inputs: list[AggregateInput] = []
        for position, ranked in enumerate(analyzed):
            item = self._evidence_item(ranked, scores[position] if position < len(scores) else None,
                                       groups[position], position)
            if item.nli_label == "entailment":
                supporting.append(item)
            elif item.nli_label == "contradiction":
                contradicting.append(item)
            else:
                neutral.append(item)
            if item.nli_label and item.nli_score is not None:
                agg_inputs.append(
                    AggregateInput(label=item.nli_label, score=item.nli_score, group=groups[position])
                )

        if passages and not analyzed:
            empty = AggregateResult(
                status=Verdict.INSUFFICIENT_EVIDENCE,
                explanation="Passages were retrieved but none passed the retrieval threshold.",
                limited_corroboration=False, support_passages=0, contradict_passages=0,
                support_sources=0, contradict_sources=0, independent_groups=0,
            )
            aggregate_result = empty
        elif not passages:
            all_failed = bool(failures) and len(failures) == len(self.adapters)
            aggregate_result = AggregateResult(
                status=Verdict.UNABLE_TO_ASSESS if all_failed else Verdict.INSUFFICIENT_EVIDENCE,
                explanation=(
                    "No source could be reached, so no evidence could be retrieved."
                    if all_failed
                    else "No evidence passages were retrieved from the permitted sources."
                ),
                limited_corroboration=False, support_passages=0, contradict_passages=0,
                support_sources=0, contradict_sources=0, independent_groups=0,
            )
        else:
            aggregate_result = aggregate(
                agg_inputs,
                tau=self.settings.verity_tau_nli,
                tau_single=self.settings.verity_tau_nli_single_source,
            )

        if not scores and analyzed:
            aggregate_result = AggregateResult(
                status=Verdict.UNABLE_TO_ASSESS,
                explanation=(
                    "Evidence was retrieved but the NLI model was unavailable, so the claim "
                    "could not be assessed."
                ),
                limited_corroboration=False, support_passages=0, contradict_passages=0,
                support_sources=0, contradict_sources=0, independent_groups=len(set(groups)),
            )

        claim_notes = list(claim.notes)
        undated = sum(1 for ranked in analyzed if not ranked.passage.published_at)
        if analyzed and undated:
            claim_notes.append(
                f"{undated} of {len(analyzed)} evidence passage(s) have no publication date; "
                "the recency of this evidence could not be verified."
            )

        assessment = ClaimAssessment(
            claim_id=f"c{index + 1}",
            text=claim.text,
            start=claim.start,
            end=claim.end,
            status=aggregate_result.status,
            explanation=aggregate_result.explanation,
            limited_corroboration=aggregate_result.limited_corroboration,
            claim_notes=claim_notes,
            stats=ClaimStats(
                passages_considered=len(analyzed),
                support_passages=aggregate_result.support_passages,
                contradict_passages=aggregate_result.contradict_passages,
                support_sources=aggregate_result.support_sources,
                contradict_sources=aggregate_result.contradict_sources,
                independent_groups=aggregate_result.independent_groups,
            ),
            supporting=supporting,
            contradicting=contradicting,
            neutral=neutral,
            fact_checks=fact_checks,
        )
        return assessment, degraded, records, failures

    @staticmethod
    def _non_verifiable(claim: ExtractedClaim, index: int, claim_type: str) -> ClaimAssessment:
        explanations = {
            OPINION_SUBJECTIVE: (
                "Subjective statement - not directly verifiable against evidence; no search "
                "verdict is given."
            ),
            PREDICTION: "Future prediction - cannot be verified against retrieved evidence.",
            ALLEGATION: (
                "Allegation about a person or organisation - reporting that an allegation exists "
                "is not evidence that it is true; no true/false verdict is given."
            ),
            UNCLEAR: "No checkable factual claim was identified in this statement.",
        }
        return ClaimAssessment(
            claim_id=f"c{index + 1}",
            text=claim.text,
            start=claim.start,
            end=claim.end,
            status=Verdict.NOT_VERIFIABLE,
            claim_type=claim_type,
            explanation=explanations.get(claim_type, "Not verifiable against retrieved evidence."),
            limited_corroboration=False,
            claim_notes=list(claim.notes),
            stats=ClaimStats(
                passages_considered=0,
                support_passages=0,
                contradict_passages=0,
                support_sources=0,
                contradict_sources=0,
                independent_groups=0,
            ),
        )

    @staticmethod
    def _unsupported_language(
        claim: ExtractedClaim, index: int, claim_type: str
    ) -> ClaimAssessment:
        return ClaimAssessment(
            claim_id=f"c{index + 1}",
            text=claim.text,
            start=claim.start,
            end=claim.end,
            status=Verdict.UNABLE_TO_ASSESS,
            claim_type=claim_type,
            explanation=(
                "This statement appears to be in a language the retrieval and entailment models "
                "do not support (they are English-first), so no true/false verdict is given."
            ),
            limited_corroboration=False,
            claim_notes=list(claim.notes)
            + [
                "Non-English input: the pretrained models are English-only, so this statement was "
                "not assessed against evidence."
            ],
            stats=ClaimStats(
                passages_considered=0,
                support_passages=0,
                contradict_passages=0,
                support_sources=0,
                contradict_sources=0,
                independent_groups=0,
            ),
        )

    @staticmethod
    def _apply_allegation_policy(assessment: ClaimAssessment) -> ClaimAssessment:
        """Never give an allegation a true/false verdict.

        The evidence pipeline has already run, so the supporting/contradicting passages remain;
        this rewrites the verdict to ``NOT_VERIFIABLE`` and discloses what the evidence shows,
        including whether an official finding appears in the retrieved text.
        """
        passages = [item.passage for item in assessment.supporting + assessment.contradicting]
        official_finding, notes = summarize_allegation(passages)
        support = len(assessment.supporting)
        contradict = len(assessment.contradicting)
        finding = (
            "An official-finding signal appears in the retrieved text - check the primary source."
            if official_finding
            else "No official finding was present in the retrieved evidence."
        )
        assessment.status = Verdict.NOT_VERIFIABLE
        assessment.limited_corroboration = False
        assessment.explanation = (
            f"Allegation about a person or organisation. {support} retrieved passage(s) support and "
            f"{contradict} contradict the allegation; VerityAI reports what the evidence shows and "
            f"does not declare the allegation true or false. {finding}"
        )
        assessment.claim_notes = list(assessment.claim_notes) + notes
        return assessment

    @staticmethod
    def _evidence_item(
        ranked: RankedPassage, score: NLIScore | None, group: int, position: int
    ) -> EvidenceItem:
        passage = ranked.passage
        return EvidenceItem(
            passage=passage.text,
            source=passage.source,
            title=passage.title,
            url=passage.url,
            publisher=passage.publisher,
            published_at=passage.published_at,
            retrieved_at=passage.retrieved_at or now_iso(),
            rank=position + 1,
            retrieval_score=ranked.retrieval_score,
            bm25_rank=ranked.bm25_rank,
            dense_rank=ranked.dense_rank,
            rrf_score=ranked.rrf_score,
            rerank_score=ranked.rerank_score,
            nli_label=score.label if score else None,
            nli_score=score.score if score else None,
            nli_probs=NLIProbabilities(**score.probs) if score else None,
            independent_group=group,
            note=passage.note,
        )

    def _model_infos(self, use_reranker: bool) -> list[ModelInfo]:
        loaded = loaded_models()
        dev = device()

        def loaded_flag(model_id: str) -> bool:
            return any(model_id in key for key in loaded)

        infos = [
            ModelInfo(
                name="dense-retrieval", model_id=self.settings.verity_bge_model_id,
                revision=self.settings.verity_bge_model_revision, role="passage/query embeddings",
                device=dev, loaded=loaded_flag(self.settings.verity_bge_model_id),
            ),
            ModelInfo(
                name="nli", model_id=self.settings.verity_nli_model_id,
                revision=self.settings.verity_nli_model_revision,
                role="evidence-claim entailment", device=dev,
                loaded=loaded_flag(self.settings.verity_nli_model_id),
            ),
        ]
        if use_reranker:
            infos.append(
                ModelInfo(
                    name="reranker", model_id=self.settings.verity_reranker_model_id,
                    revision=self.settings.verity_reranker_revision, role="cross-encoder relevance",
                    device=dev, loaded=loaded_flag(self.settings.verity_reranker_model_id),
                )
            )
        return infos
