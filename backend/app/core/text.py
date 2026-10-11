"""Deterministic text utilities: whitespace, tokenization, sentence splitting,
entity/number/date hints, shingles and Jaccard similarity.

No external NLP model is required here. Sentence segmentation is a deterministic
regex scanner that keeps character offsets into the *original* text so extracted
claims can be mapped back to their source position.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WS = re.compile(r"\s+")
# Unicode-aware: ``[^\W_]`` is a word character (letters/digits), excluding underscore, in any
# script. This keeps ASCII tokenization identical while letting non-Latin scripts (e.g. Devanagari)
# produce tokens instead of collapsing to none.
_TOKEN = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*")

_TITLES = {
    "mr", "mrs", "ms", "dr", "prof", "st", "mt", "sr", "jr", "gen", "sen", "rep",
    "gov", "capt", "lt", "col", "sgt", "rev", "hon", "pres", "supt", "det", "insp",
    "messrs", "mmes", "fr", "br",
}

_BOUNDARY = re.compile(r"([.!?]+)(\s+|$)")
_ENTITY = re.compile(r"\b(?:[A-Z][a-z]{1,}|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]{1,}|[A-Z]{2,}))*\b")
_YEAR = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
_NUMBER = re.compile(r"\b\d[\d,.]*\b")

_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or", "is", "are",
    "was", "were", "be", "been", "being", "by", "with", "as", "that", "this", "these",
    "those", "it", "its", "from", "has", "have", "had", "do", "does", "did", "but",
    "not", "no", "which", "who", "whom", "what", "when", "where", "why", "how",
}

_DETERMINERS = {"the", "a", "an", "this", "that", "these", "those"}

_OPINION_MARKERS = re.compile(
    r"\b(i think|i believe|i feel|in my opinion|imo|i guess|personally)\b", re.IGNORECASE
)
_VERB_HINT = re.compile(
    r"\b(is|are|was|were|has|have|had|will|would|can|could|may|might|must|do|does|did|"
    r"[a-z]{4,}ed|[a-z]{3,}s)\b"
)


@dataclass(frozen=True)
class Sentence:
    text: str
    start: int
    end: int


def normalize_whitespace(text: str) -> str:
    return _WS.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def content_tokens(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in _STOPWORDS]


def _last_word(prefix: str) -> str:
    match = re.search(r"([A-Za-z.]+)\s*$", prefix)
    return match.group(1) if match else ""


def _is_boundary(text: str, match: re.Match[str]) -> bool:
    punct = match.group(1)
    nxt = text[match.end() : match.end() + 1]
    last = _last_word(text[: match.start()])

    if last.lower().strip(".") in _TITLES:
        return False
    if re.fullmatch(r"[A-Za-z]", last):
        return False
    if nxt and nxt.isdigit():
        return False
    if punct[-1] == "." and nxt and nxt.islower():
        return False
    return True


def split_sentences(text: str) -> list[Sentence]:
    """Split ``text`` into sentences, preserving offsets into the original string."""
    out: list[Sentence] = []
    start = 0
    for match in _BOUNDARY.finditer(text):
        if not _is_boundary(text, match):
            continue
        chunk = text[start : match.start() + 1]
        if chunk.strip():
            out.append(Sentence(chunk.strip(), start, match.start() + 1))
        start = match.end()
    if start < len(text):
        tail = text[start:]
        if tail.strip():
            out.append(Sentence(tail.strip(), start, len(text)))
    return out


def entity_hints(text: str, limit: int = 6) -> list[str]:
    """Lightweight proper-noun candidates (no model dependency)."""
    seen: list[str] = []
    for raw in _ENTITY.findall(text):
        parts = normalize_whitespace(raw).split(" ")
        while parts and parts[0].lower() in _DETERMINERS:
            parts.pop(0)
        cand = " ".join(parts)
        if len(cand) < 3 or cand in seen:
            continue
        if cand.lower() in _STOPWORDS:
            continue
        seen.append(cand)
        if len(seen) >= limit:
            break
    return seen


def has_number(text: str) -> bool:
    return bool(_NUMBER.search(text))


def has_year(text: str) -> bool:
    return bool(_YEAR.search(text))


def has_negation(text: str) -> bool:
    return bool(re.search(r"\b(not|no|never|none|neither|nor|without|cannot|can't|isn't|"
                          r"wasn't|aren't|weren't|doesn't|don't|didn't)\b", text, re.I))


def looks_like_claim(sentence: str) -> bool:
    """Cautious declarative-claim filter. Deliberately permissive but rejects
    questions, opinions and fragments so we never present non-claims as claims."""
    text = normalize_whitespace(sentence)
    if not text or text.endswith("?"):
        return False
    tokens = tokenize(text)
    if len(tokens) < 5 or len(tokens) > 70:
        return False
    if _OPINION_MARKERS.search(text):
        return False
    if re.match(r"^[-*•\d.)\s]+$", text):
        return False
    if not _VERB_HINT.search(text):
        return False
    return True


def shingles(text: str, n: int = 5) -> frozenset[int]:
    tokens = tokenize(text)
    if not tokens:
        return frozenset()
    grams = [" ".join(tokens[i : i + n]) for i in range(max(1, len(tokens) - n + 1))]
    return frozenset(hash(g) for g in grams)


def jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    # An empty shingle set means "no comparable content"; it must never count as a duplicate.
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def domain_of(url: str) -> str:
    match = re.match(r"^[a-zA-Z]+://([^/]+)", url or "")
    host = (match.group(1) if match else (url or "")).lower()
    return host.split("@")[-1].split(":")[0]
