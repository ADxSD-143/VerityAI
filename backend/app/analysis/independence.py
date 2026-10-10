"""Source independence.

Two passages are one independent source if they come from the same document or are
near-duplicates of each other (syndicated / re-published copies). Duplicated
reporting must not be counted as independent corroboration.
"""

from __future__ import annotations

from ..core.text import jaccard, shingles
from ..sources.base import EvidencePassage

_MAX_PAIRWISE = 160


def document_key(passage: EvidencePassage) -> str:
    if passage.page_id:
        return f"{passage.source}:{passage.page_id}"
    if passage.url:
        return passage.url.split("#", 1)[0]
    return f"{passage.source}:{passage.title}"


def cluster_passages(
    texts: list[str], doc_keys: list[str], threshold: float = 0.8
) -> list[int]:
    n = len(texts)
    if n == 0:
        return []
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    first_by_doc: dict[str, int] = {}
    for i, key in enumerate(doc_keys):
        if key in first_by_doc:
            union(first_by_doc[key], i)
        else:
            first_by_doc[key] = i

    limit = min(n, _MAX_PAIRWISE)
    grams = [shingles(texts[i]) for i in range(limit)]
    for i in range(limit):
        for j in range(i + 1, limit):
            if find(i) == find(j):
                continue
            if jaccard(grams[i], grams[j]) >= threshold:
                union(i, j)

    roots: dict[int, int] = {}
    groups: list[int] = []
    for i in range(n):
        root = find(i)
        if root not in roots:
            roots[root] = len(roots)
        groups.append(roots[root])
    return groups
