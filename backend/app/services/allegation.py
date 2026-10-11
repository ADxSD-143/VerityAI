"""Allegation handling.

The output contract requires that the **existence of an allegation is never collapsed into the
truth of the allegation**: VerityAI reports what the evidence shows (supporting / contradicting
passages, and whether an official finding appears), and does not declare the allegation true or
false.

This module provides a deliberately conservative, surface-level read of retrieved text: it detects
*official-finding* language (e.g. "convicted", "acquitted") versus *allegation-framing* language
(e.g. "alleged", "accused", "charged"). It never infers a verdict from these markers; it only
shapes the disclosure.
"""

from __future__ import annotations

import re

_OFFICIAL_FINDING = re.compile(
    r"\b(convicted|conviction|found guilty|found not guilty|acquitted|acquittal|cleared of|"
    r"exonerated|court ruled|court found|judge ruled|jury found|pleaded guilty|sentenced|"
    r"charges dropped|investigation found|substantiated)\b",
    re.IGNORECASE,
)
_ALLEGATION_FRAMING = re.compile(
    r"\b(alleged|allegedly|allegation|accused|accusation|charged with|indicted|"
    r"rumou?red|suspect(?:ed)?|under investigation)\b",
    re.IGNORECASE,
)


def summarize_allegation(passages: list[str]) -> tuple[bool, list[str]]:
    """Return ``(official_finding_present, notes)`` for the retrieved passages.

    ``official_finding_present`` is true only when a passage contains explicit official-finding
    language. It is a signal to surface for the reader, **not** an adjudication.
    """
    established = any(_OFFICIAL_FINDING.search(text or "") for text in passages)
    framing = any(_ALLEGATION_FRAMING.search(text or "") for text in passages)

    notes: list[str] = []
    if established:
        notes.append(
            "A retrieved passage contains official-finding language (e.g. 'convicted'/'acquitted'); "
            "an official finding is not the same as an allegation - verify the primary source."
        )
    elif framing:
        notes.append(
            "Retrieved passages refer to the allegation itself; no official finding was present in "
            "the retrieved evidence."
        )
    else:
        notes.append("No official finding was present in the retrieved evidence.")
    return established, notes
