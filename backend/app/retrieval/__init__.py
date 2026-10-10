"""Retrieval: lexical (BM25), dense (BGE), fusion (RRF), optional reranking."""

from .dense import DenseIndex, EmbeddingCache
from .fusion import deduplicate, merge_rank_map, rrf_fuse
from .lexical import BM25Index
from .pipeline import RankedPassage, RetrievalOutcome, retrieve

__all__ = [
    "BM25Index",
    "DenseIndex",
    "EmbeddingCache",
    "RankedPassage",
    "RetrievalOutcome",
    "deduplicate",
    "merge_rank_map",
    "retrieve",
    "rrf_fuse",
]
