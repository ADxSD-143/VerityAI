"""Builds the active source adapters from configuration."""

from __future__ import annotations

from ..config import Settings
from .base import SourceAdapter
from .factcheck import FactCheckAdapter
from .openalex import OpenAlexAdapter
from .wikidata import WikidataAdapter
from .wikipedia import WikipediaAdapter


def build_adapters(settings: Settings) -> list[SourceAdapter]:
    ua = settings.verity_user_agent
    return [
        WikipediaAdapter(
            lang=settings.verity_wikipedia_lang,
            user_agent=ua,
            max_pages=settings.verity_max_pages_per_source,
            timeout=settings.verity_source_timeout_s,
        ),
        WikidataAdapter(user_agent=ua, timeout=settings.verity_source_timeout_s),
        OpenAlexAdapter(
            user_agent=ua,
            mailto=settings.openalex_mailto,
            timeout=settings.verity_source_timeout_s,
        ),
        FactCheckAdapter(
            user_agent=ua,
            api_key=settings.factcheck_api_key,
            timeout=settings.verity_source_timeout_s,
        ),
    ]


__all__ = [
    "FactCheckAdapter",
    "OpenAlexAdapter",
    "SourceAdapter",
    "WikidataAdapter",
    "WikipediaAdapter",
    "build_adapters",
]
