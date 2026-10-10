"""Optional cross-encoder reranking.

Applied only to a bounded candidate pool from the hybrid stage. The reranker's
output is a *relevance* score, never a truth score.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..models_io import get_cross_encoder


class CrossEncoderReranker:
    def __init__(self, model_id: str, revision: str | None = None) -> None:
        self.model_id = model_id
        self.model: Any = get_cross_encoder(model_id, revision)

    def rerank(self, query: str, texts: list[str], top_k: int) -> list[tuple[int, float]]:
        if not texts:
            return []
        pairs = [(query, text) for text in texts]
        scores = np.asarray(self.model.predict(pairs, show_progress_bar=False))
        order = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in order]
