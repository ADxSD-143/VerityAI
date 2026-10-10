"""BM25 lexical retrieval (``rank_bm25``).

BM25 is the lexical arm of the hybrid retriever: it is what makes exact names,
dates, quantities and technical terms retrievable even when the dense model would
blur them. TF-IDF is kept out of the runtime path (it appears only as an
evaluation baseline under ``experiments/``).
"""

from __future__ import annotations

from rank_bm25 import BM25Okapi

from ..core.text import tokenize


class BM25Index:
    def __init__(self, docs: list[str]) -> None:
        self.corpus_tokens = [tokenize(doc) or ["<empty>"] for doc in docs]
        self._bm25 = BM25Okapi(self.corpus_tokens) if self.corpus_tokens else None

    def rank(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if self._bm25 is None:
            return []
        tokens = tokenize(query) or ["<empty>"]
        scores = self._bm25.get_scores(tokens)
        order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
        out: list[tuple[int, float]] = []
        for idx in order[:top_k]:
            score = float(scores[idx])
            if score <= 0.0:
                continue
            out.append((idx, score))
        return out
