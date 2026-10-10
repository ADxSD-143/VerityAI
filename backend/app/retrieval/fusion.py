"""Reciprocal Rank Fusion and near-duplicate removal.

RRF combines rankers by rank rather than score, which avoids mixing BM25's
unbounded scores with cosine similarities:

    RRF(d) = sum_i  weight_i / (k + rank_i(d))

``rank_i(d)`` is the 0-based rank of document ``d`` in ranker ``i``; ``k`` is the
smoothing constant (60 by convention). Near-duplicate passages are removed after
fusion so syndicated copies do not inflate the evidence count.
"""

from __future__ import annotations

from ..core.text import jaccard, shingles


def rrf_fuse(
    rankings: list[list[int]], k: int = 60, weights: list[float] | None = None
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for r_i, ranking in enumerate(rankings):
        weight = weights[r_i] if weights else 1.0
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + weight / (k + rank + 1)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def merge_rank_map(ranking: list[int]) -> dict[int, int]:
    return {idx: rank + 1 for rank, idx in enumerate(ranking)}


def deduplicate(indices: list[int], texts: list[str], threshold: float = 0.8) -> list[int]:
    kept: list[int] = []
    kept_shingles: list[frozenset[int]] = []
    for idx in indices:
        gram = shingles(texts[idx])
        if any(jaccard(gram, prior) >= threshold for prior in kept_shingles):
            continue
        kept.append(idx)
        kept_shingles.append(gram)
    return kept
