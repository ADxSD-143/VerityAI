"""Deterministic, zero-cost claim-type pre-classification (Phase 2 start).

Rules only — no model. The output contract requires that a statement be classified before it is
checked, and that a **true/false verdict is never forced** on something that is not a checkable
fact. This module produces the type; ``backend/app/services/analyzer.py`` uses it to route
non-fact statements to ``NOT_VERIFIABLE`` instead of running the evidence pipeline.

Types: ``CHECKABLE_FACT``, ``OPINION_SUBJECTIVE``, ``PREDICTION``, ``ALLEGATION``, ``UNCLEAR``.

This is an intentionally conservative first pass. It is unit-tested; its accuracy against a
human-labelled set is a Phase 2 evaluation gate that is still open (see ``docs/EVALUATION.md``).
"""

from __future__ import annotations

import re

CHECKABLE_FACT = "CHECKABLE_FACT"
OPINION_SUBJECTIVE = "OPINION_SUBJECTIVE"
PREDICTION = "PREDICTION"
ALLEGATION = "ALLEGATION"
UNCLEAR = "UNCLEAR"

CLAIM_TYPES = (CHECKABLE_FACT, OPINION_SUBJECTIVE, PREDICTION, ALLEGATION, UNCLEAR)

#: types that must never receive a SUPPORTED/REFUTED verdict.
NON_FACT_TYPES = frozenset({OPINION_SUBJECTIVE, PREDICTION, ALLEGATION, UNCLEAR})

_ALLEGATION = re.compile(
    r"\b(accused of|allegedly|alleged|charged with|indicted|suspect(?:ed)? of|"
    r"rumou?red to|allegations?|acquitted of|convicted of)\b",
    re.IGNORECASE,
)
_OPINION = re.compile(
    r"\b(i think|i believe|i feel|in my opinion|imo|personally|the best|the worst|"
    r"the greatest|the hottest|the most beautiful|the ugliest|overrated|underrated|"
    r"better than|worse than|should|is the best|is the worst)\b",
    re.IGNORECASE,
)
_PREDICTION = re.compile(
    r"\b(will|won't|will not|going to|gonna|predict|predicts|forecast|by 20\d{2}|"
    r"next year|next decade|next season)\b",
    re.IGNORECASE,
)
_UNCLEAR = re.compile(
    r"^(things|stuff|it|this|that|they|everyone|nobody|everything|nothing|"
    r"the situation|the system|the government)\b",
    re.IGNORECASE,
)


def classify_claim_type(text: str) -> str:
    """Classify a statement into one of ``CLAIM_TYPES`` using deterministic rules."""
    statement = (text or "").strip()
    if len(statement) < 8:
        return UNCLEAR
    if _ALLEGATION.search(statement):
        return ALLEGATION
    if _OPINION.search(statement):
        return OPINION_SUBJECTIVE
    if _PREDICTION.search(statement):
        return PREDICTION
    if statement.endswith("?") or _UNCLEAR.search(statement):
        return UNCLEAR
    return CHECKABLE_FACT
