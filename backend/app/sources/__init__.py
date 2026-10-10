"""Evidence sources."""

from .base import (
    EvidencePassage,
    FactCheckRecord,
    SourceAdapter,
    SourceResult,
    now_iso,
)
from .registry import build_adapters

__all__ = [
    "EvidencePassage",
    "FactCheckRecord",
    "SourceAdapter",
    "SourceResult",
    "build_adapters",
    "now_iso",
]
