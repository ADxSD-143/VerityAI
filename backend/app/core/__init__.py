"""Core package: configuration, text utilities, errors."""

from .errors import (
    InputValidationError,
    ModelLoadError,
    SourceError,
    UrlFetchError,
    UrlSafetyError,
    VerityError,
)

__all__ = [
    "InputValidationError",
    "ModelLoadError",
    "SourceError",
    "UrlFetchError",
    "UrlSafetyError",
    "VerityError",
]
