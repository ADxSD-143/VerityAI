"""Lazy, process-wide model registry.

Models are heavy, so nothing is loaded until it is first needed, and each model is
loaded at most once per process (guarded by a lock). Load failures are turned into
``ModelLoadError`` with a readable message and remembered, so repeated requests
fail fast instead of re-attempting a broken download.
"""

from __future__ import annotations

import threading
from typing import Any

from .config import get_settings
from .core.errors import ModelLoadError

_lock = threading.Lock()
_models: dict[str, Any] = {}
_failed: dict[str, str] = {}


def _key(kind: str, model_id: str, revision: str | None) -> str:
    return f"{kind}:{model_id}@{revision or 'default'}"


def _device() -> str:
    settings = get_settings()
    device = settings.verity_device
    if device == "cuda":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # noqa: BLE001
            device = "cpu"
    if settings.verity_torch_threads:
        try:
            import torch

            torch.set_num_threads(settings.verity_torch_threads)
        except Exception:  # noqa: BLE001
            pass
    return device


def device() -> str:
    return _device()


def _record_failure(key: str, exc: Exception) -> ModelLoadError:
    _failed[key] = str(exc)
    return ModelLoadError(
        f"Could not load model '{key}'. The model may not be downloaded, the network "
        f"may be unavailable, or the cache is corrupt. Underlying error: {exc}"
    )


def get_sentence_transformer(model_id: str, revision: str | None = None) -> Any:
    key = _key("sentence-transformer", model_id, revision)
    with _lock:
        if key in _models:
            return _models[key]
        if key in _failed:
            raise ModelLoadError(f"Model '{key}' previously failed to load: {_failed[key]}")
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_id, device=_device(), revision=revision)
        except Exception as exc:  # noqa: BLE001
            raise _record_failure(key, exc) from exc
        _models[key] = model
        return model


def get_nli_components(model_id: str, revision: str | None = None) -> tuple[Any, Any]:
    key = _key("nli", model_id, revision)
    with _lock:
        if key in _models:
            return _models[key]
        if key in _failed:
            raise ModelLoadError(f"Model '{key}' previously failed to load: {_failed[key]}")
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
            model = AutoModelForSequenceClassification.from_pretrained(model_id, revision=revision)
            model.to(_device())
            model.eval()
        except Exception as exc:  # noqa: BLE001
            raise _record_failure(key, exc) from exc
        _models[key] = (tokenizer, model)
        return _models[key]


def get_cross_encoder(model_id: str, revision: str | None = None) -> Any:
    key = _key("cross-encoder", model_id, revision)
    with _lock:
        if key in _models:
            return _models[key]
        if key in _failed:
            raise ModelLoadError(f"Model '{key}' previously failed to load: {_failed[key]}")
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(model_id, device=_device(), revision=revision)
        except Exception as exc:  # noqa: BLE001
            raise _record_failure(key, exc) from exc
        _models[key] = model
        return model


def loaded_models() -> list[str]:
    return sorted(_models.keys())


def failed_models() -> dict[str, str]:
    return dict(_failed)
