"""Analysis: NLI, source independence, conservative aggregation."""

from .aggregation import AggregateInput, AggregateResult, aggregate
from .independence import cluster_passages, document_key
from .nli import CANONICAL_LABELS, NLIModel, NLIScore, canonicalize_label

__all__ = [
    "CANONICAL_LABELS",
    "AggregateInput",
    "AggregateResult",
    "NLIModel",
    "NLIScore",
    "aggregate",
    "canonicalize_label",
    "cluster_passages",
    "document_key",
]
