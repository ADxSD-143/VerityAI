"""Retrieval orchestration: BM25 + BGE -> RRF -> dedup -> optional rerank.

If the dense model cannot be loaded the pipeline degrades to BM25-only and says so
explicitly (``degraded=True`` + a reason) rather than silently pretending to be
semantic.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

from ..config import get_settings
from ..core.errors import ModelLoadError
from ..models_io import get_sentence_transformer
from ..sources.base import EvidencePassage
from .dense import DenseIndex, EmbeddingCache
from .fusion import deduplicate, merge_rank_map, rrf_fuse
from .lexical import BM25Index
from .rerank import CrossEncoderReranker

DUPLICATE_JACCARD = 0.8


@dataclass
class RankedPassage:
    index: int
    passage: EvidencePassage
    bm25_rank: int | None
    dense_rank: int | None
    rrf_score: float
    rerank_score: float | None
    retrieval_score: float


@dataclass
class RetrievalOutcome:
    ranked: list[RankedPassage] = field(default_factory=list)
    degraded: bool = False
    degraded_reasons: list[str] = field(default_factory=list)
    n_candidates: int = 0


def default_embedding_cache() -> EmbeddingCache:
    settings = get_settings()
    path = settings.verity_embed_cache_dir or os.path.join(
        tempfile.gettempdir(), "verity-embed-cache"
    )
    return EmbeddingCache(path)


def retrieve(
    claim: str,
    passages: list[EvidencePassage],
    *,
    top_k: int | None = None,
    use_reranker: bool | None = None,
    rrf_k: int | None = None,
    cache: EmbeddingCache | None = None,
    rerank_pool: int = 30,
) -> RetrievalOutcome:
    settings = get_settings()
    top_k = top_k or settings.verity_top_k_retrieval
    if use_reranker is None:
        use_reranker = settings.verity_use_reranker
    rrf_k = rrf_k or settings.verity_rrf_k
    cache = cache or default_embedding_cache()

    outcome = RetrievalOutcome(n_candidates=len(passages))
    if not passages:
        return outcome

    texts = [p.text for p in passages]
    candidate_pool = max(top_k * 3, 30)

    bm25_order = [idx for idx, _ in BM25Index(texts).rank(claim, candidate_pool)]

    dense_order: list[int] = []
    try:
        model = get_sentence_transformer(
            settings.verity_bge_model_id, settings.verity_bge_model_revision
        )
        dense = DenseIndex(texts, model, settings.verity_bge_model_id, cache=cache)
        dense_order = [idx for idx, _ in dense.rank(claim, candidate_pool)]
    except ModelLoadError as exc:
        outcome.degraded = True
        outcome.degraded_reasons.append(f"dense retrieval unavailable: {exc}")

    rankings = [r for r in (bm25_order, dense_order) if r]
    if settings.verity_retrieval_mode == "dense" and dense_order:
        rankings = [dense_order]
    if not rankings:
        return outcome

    fused = rrf_fuse(rankings, k=rrf_k, weights=[1.0] * len(rankings))
    rrf_map = dict(fused)
    order = deduplicate([idx for idx, _ in fused], texts, threshold=DUPLICATE_JACCARD)

    rerank_map: dict[int, float] = {}
    if use_reranker and order:
        try:
            reranker = CrossEncoderReranker(
                settings.verity_reranker_model_id, settings.verity_reranker_revision
            )
            pool = order[:rerank_pool]
            reranked = reranker.rerank(claim, [texts[i] for i in pool], len(pool))
            rerank_map = {pool[local]: score for local, score in reranked}
            order = [pool[local] for local, _ in reranked] + order[len(pool):]
        except ModelLoadError as exc:
            outcome.degraded = True
            outcome.degraded_reasons.append(f"reranker unavailable: {exc}")

    bm25_map = merge_rank_map(bm25_order)
    dense_map = merge_rank_map(dense_order)

    ranked: list[RankedPassage] = []
    for idx in order[:top_k]:
        rerank_score = rerank_map.get(idx) if rerank_map else None
        ranked.append(
            RankedPassage(
                index=idx,
                passage=passages[idx],
                bm25_rank=bm25_map.get(idx),
                dense_rank=dense_map.get(idx),
                rrf_score=rrf_map.get(idx, 0.0),
                rerank_score=rerank_score,
                retrieval_score=rerank_score
                if (use_reranker and rerank_score is not None)
                else rrf_map.get(idx, 0.0),
            )
        )
    outcome.ranked = ranked
    return outcome
