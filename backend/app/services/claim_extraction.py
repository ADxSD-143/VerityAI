"""Claim extraction.

A single user-supplied claim keeps its original wording. Long text is segmented
deterministically into sentences, filtered with a cautious declarative-claim
heuristic, and each kept claim keeps its original character span. Non-claims
(questions, opinions, fragments) are dropped rather than forced into a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.text import (
    content_tokens,
    entity_hints,
    has_negation,
    has_number,
    has_year,
    looks_like_claim,
    normalize_whitespace,
    split_sentences,
)


@dataclass
class ExtractedClaim:
    text: str
    start: int | None
    end: int | None
    source: str  # "input" | "article"
    notes: list[str] = field(default_factory=list)


def _notes_for(text: str) -> list[str]:
    notes: list[str] = []
    if has_year(text):
        notes.append("contains a date/year")
    elif has_number(text):
        notes.append("contains a numeric quantity")
    if has_negation(text):
        notes.append("contains negation")
    entities = entity_hints(text)
    if entities:
        notes.append("entities: " + ", ".join(entities[:4]))
    return notes


def single_claim(text: str) -> list[ExtractedClaim]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    notes: list[str] = []
    if not looks_like_claim(cleaned):
        notes.append(
            "input does not look like a declarative factual claim; the assessment "
            "may be unreliable"
        )
    return [ExtractedClaim(text=cleaned, start=None, end=None, source="input", notes=notes)]


def extract_claims(text: str, *, max_claims: int) -> list[ExtractedClaim]:
    sentences = split_sentences(text)
    claims: list[ExtractedClaim] = []
    for sentence in sentences:
        if not looks_like_claim(sentence.text):
            continue
        claims.append(
            ExtractedClaim(
                text=normalize_whitespace(sentence.text),
                start=sentence.start,
                end=sentence.end,
                source="article",
                notes=_notes_for(sentence.text),
            )
        )
        if len(claims) >= max_claims:
            break
    if not claims:
        cleaned = normalize_whitespace(text)
        if cleaned:
            claims.append(
                ExtractedClaim(
                    text=cleaned[:1000],
                    start=0,
                    end=len(text),
                    source="article",
                    notes=["could not segment clear claims; treated the text as one statement"],
                )
            )
    return claims


def query_variants(claim: str, max_variants: int = 3) -> list[str]:
    variants = [normalize_whitespace(claim)]
    entities = entity_hints(claim)
    if entities:
        variants.append(" ".join(entities[:4]))
    tokens = content_tokens(claim)
    if len(tokens) >= 4:
        variants.append(" ".join(tokens[:12]))
    out: list[str] = []
    for variant in variants:
        variant = normalize_whitespace(variant)
        if variant and variant not in out:
            out.append(variant)
    return out[:max_variants]
