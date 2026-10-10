"""Measure real model sizes, cold-load times and inference latency on this machine.

Nothing is assumed: every number is measured at run time and written to
``experiments/results/measure_resources.json``.

Usage:
    python experiments/measure_resources.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from _common import save_json  # noqa: E402
from app.analysis.nli import NLIModel  # noqa: E402
from app.models_io import (  # noqa: E402
    device,
    get_cross_encoder,
    get_nli_components,
    get_sentence_transformer,
    loaded_models,
)

BGE = "BAAI/bge-small-en-v1.5"
NLI = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def hf_cache_root() -> Path:
    return Path(os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface"))


def model_dir_size(model_id: str) -> int | None:
    path = hf_cache_root() / "hub" / ("models--" + model_id.replace("/", "--"))
    return dir_size(path) if path.exists() else None


def main() -> None:
    results: dict = {"device": device()}

    start = time.perf_counter()
    model = get_sentence_transformer(BGE)
    results["bge_load_s"] = round(time.perf_counter() - start, 3)
    start = time.perf_counter()
    model.encode(["A short sentence about Paris."] * 8, normalize_embeddings=True,
                 show_progress_bar=False)
    results["bge_encode_8_batch_ms"] = round((time.perf_counter() - start) * 1000, 2)
    results["bge_dir_bytes"] = model_dir_size(BGE)

    start = time.perf_counter()
    get_nli_components(NLI)
    results["nli_load_s"] = round(time.perf_counter() - start, 3)
    nli = NLIModel(NLI)
    pairs = [("Paris is the capital of France.", "Paris is the capital of France.")] * 4
    start = time.perf_counter()
    nli.predict_batch(pairs)
    results["nli_predict_4_batch_ms"] = round((time.perf_counter() - start) * 1000, 2)
    results["nli_dir_bytes"] = model_dir_size(NLI)
    results["nli_label_map"] = {str(k): v for k, v in nli.label_map.items()}

    try:
        start = time.perf_counter()
        encoder = get_cross_encoder(RERANKER)
        results["reranker_load_s"] = round(time.perf_counter() - start, 3)
        start = time.perf_counter()
        encoder.predict([("query", "document")] * 8, show_progress_bar=False)
        results["reranker_predict_8_batch_ms"] = round((time.perf_counter() - start) * 1000, 2)
        results["reranker_dir_bytes"] = model_dir_size(RERANKER)
    except Exception as exc:  # noqa: BLE001
        results["reranker_error"] = str(exc)

    results["loaded_models"] = loaded_models()
    path = save_json("measure_resources.json", results)
    print(json.dumps(results, indent=2))
    print("\nWrote", path)


if __name__ == "__main__":
    main()
