"""Dense semantic retrieval with BGE sentence embeddings.

Query/instruction handling follows the ``BAAI/bge-*-en-v1.5`` model cards: retrieval
*queries* are prefixed with the recommended instruction, passages are encoded plain,
and both sides are L2-normalized so cosine similarity is a plain dot product.

Embeddings are cached (in memory and optionally on disk, keyed by model id + text)
so an unchanged passage is never re-embedded.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

import numpy as np

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingCache:
    def __init__(self, path: str | None = None) -> None:
        self.path = path
        if path:
            os.makedirs(path, exist_ok=True)
        self._mem: dict[str, np.ndarray] = {}

    @staticmethod
    def _key(model_id: str, text: str) -> str:
        digest = hashlib.sha256(f"{model_id}\x00{text}".encode()).hexdigest()
        return digest

    def get(self, model_id: str, text: str) -> np.ndarray | None:
        key = self._key(model_id, text)
        if key in self._mem:
            return self._mem[key]
        if self.path:
            file_path = os.path.join(self.path, key + ".npy")
            if os.path.exists(file_path):
                try:
                    vector = np.load(file_path)
                    self._mem[key] = vector
                    return vector
                except Exception:  # noqa: BLE001
                    return None
        return None

    def set(self, model_id: str, text: str, vector: np.ndarray) -> None:
        key = self._key(model_id, text)
        self._mem[key] = vector
        if self.path:
            try:
                np.save(os.path.join(self.path, key + ".npy"), vector)
            except Exception:  # noqa: BLE001
                pass


class DenseIndex:
    def __init__(
        self,
        docs: list[str],
        model: Any,
        model_id: str,
        *,
        cache: EmbeddingCache | None = None,
        batch_size: int = 32,
    ) -> None:
        self.model = model
        self.model_id = model_id
        self.cache = cache
        self.matrix = self._encode_docs(docs, batch_size)

    def _encode_docs(self, docs: list[str], batch_size: int) -> np.ndarray:
        if not docs:
            return np.zeros((0, 0), dtype=np.float32)
        vectors: list[np.ndarray | None] = [None] * len(docs)
        missing_idx: list[int] = []
        missing_text: list[str] = []
        for i, text in enumerate(docs):
            cached = self.cache.get(self.model_id, text) if self.cache else None
            if cached is None:
                missing_idx.append(i)
                missing_text.append(text)
            else:
                vectors[i] = cached
        if missing_text:
            encoded = self.model.encode(
                missing_text,
                batch_size=batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for offset, i in enumerate(missing_idx):
                vectors[i] = encoded[offset]
                if self.cache:
                    self.cache.set(self.model_id, docs[i], encoded[offset])
        stacked = np.vstack([np.asarray(v, dtype=np.float32) for v in vectors])
        return stacked

    def rank(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if self.matrix.size == 0:
            return []
        query_vec = self.model.encode(
            [BGE_QUERY_PREFIX + query],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        similarities = self.matrix @ query_vec
        order = np.argsort(-similarities)[:top_k]
        return [(int(i), float(similarities[i])) for i in order]
