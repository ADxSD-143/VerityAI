"""Services: claim extraction, SSRF-safe URL fetch, end-to-end analysis."""

from .claim_extraction import ExtractedClaim, extract_claims, query_variants, single_claim

__all__ = [
    "ExtractedClaim",
    "extract_claims",
    "query_variants",
    "single_claim",
]
