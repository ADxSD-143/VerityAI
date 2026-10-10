"""Shared error types.

Every error carries a stable machine code so the API layer can translate it into a
status code and a safe public message without leaking tracebacks or paths.
"""

from __future__ import annotations

from typing import Any


class VerityError(Exception):
    code = "verity_error"
    http_status = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InputValidationError(VerityError):
    code = "invalid_input"
    http_status = 422


class UrlSafetyError(VerityError):
    code = "unsafe_url"
    http_status = 400


class UrlFetchError(VerityError):
    code = "url_fetch_failed"
    http_status = 502


class ModelLoadError(VerityError):
    code = "model_load_failed"
    http_status = 503


class SourceError(VerityError):
    code = "source_error"
    http_status = 502
