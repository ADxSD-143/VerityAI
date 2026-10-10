"""Natural Language Inference over (premise = evidence passage, hypothesis = claim).

The class order is never assumed: it is read from the loaded model config's
``id2label`` and validated against the three canonical labels. A model whose labels
do not resolve cleanly is rejected at load time rather than silently mis-mapped.

Scores are model outputs for a specific evidence-claim pair. They are NOT the
probability that the claim is true.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from ..models_io import device as resolve_device
from ..models_io import get_nli_components

CANONICAL_LABELS = ("entailment", "neutral", "contradiction")


def canonicalize_label(raw: str) -> str | None:
    text = str(raw).lower()
    if "entail" in text:
        return "entailment"
    if "contradict" in text:
        return "contradiction"
    if "neutral" in text:
        return "neutral"
    return None


@dataclass
class NLIScore:
    label: str
    score: float
    probs: dict[str, float]


class NLIModel:
    def __init__(self, model_id: str, revision: str | None = None) -> None:
        self.model_id = model_id
        self.revision = revision
        tokenizer, model = get_nli_components(model_id, revision)
        self.tokenizer = tokenizer
        self.model = model
        self.device = resolve_device()
        self.label_map = self._resolve_label_map(model.config)

    @staticmethod
    def _resolve_label_map(config) -> dict[int, str]:
        id2label = getattr(config, "id2label", None) or {}
        mapping: dict[int, str] = {}
        for idx, raw in id2label.items():
            canonical = canonicalize_label(raw)
            if canonical is None:
                raise ValueError(f"Unrecognised NLI label '{raw}' at index {idx}")
            mapping[int(idx)] = canonical
        missing = [label for label in CANONICAL_LABELS if label not in mapping.values()]
        if missing or len(mapping) != len(CANONICAL_LABELS):
            raise ValueError(
                f"NLI model labels are not the three canonical classes. "
                f"Missing={missing}, resolved mapping={mapping}"
            )
        return mapping

    def predict(self, premise: str, hypothesis: str) -> NLIScore:
        return self.predict_batch([(premise, hypothesis)])[0]

    def predict_batch(
        self, pairs: list[tuple[str, str]], batch_size: int = 16
    ) -> list[NLIScore]:
        results: list[NLIScore] = []
        for start in range(0, len(pairs), batch_size):
            chunk = pairs[start : start + batch_size]
            premises = [p for p, _ in chunk]
            hypotheses = [h for _, h in chunk]
            encoded = self.tokenizer(
                premises,
                hypotheses,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt",
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            with torch.no_grad():
                logits = self.model(**encoded).logits
            probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
            for row in probabilities:
                dist = {
                    self.label_map[i]: float(row[i])
                    for i in range(len(row))
                    if i in self.label_map
                }
                for label in CANONICAL_LABELS:
                    dist.setdefault(label, 0.0)
                best = max(dist, key=dist.get)
                results.append(NLIScore(label=best, score=float(dist[best]), probs=dist))
        return results
