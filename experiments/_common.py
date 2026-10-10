"""Shared helpers for the evaluation scripts.

Everything here is deterministic and writes machine-readable artefacts under
``experiments/results/``. Nothing fabricates: when a network fetch fails the caller
records the failure and reports it.
"""

from __future__ import annotations

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "experiments" / "results"
CORPUS_DIR = ROOT / "data" / "fever_corpus"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "VerityAI-eval/0.1 (academic evaluation; contact: adityanarayansd@gmail.com)"

FEVER_LABELS = ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO")
LABEL_TO_NLI = {"SUPPORTS": "entailment", "REFUTES": "contradiction", "NOT ENOUGH INFO": "neutral"}

_FEVER_TITLE_SUBSTITUTIONS = (
    ("-LRB-", "("), ("-RRB-", ")"),
    ("-LSB-", "["), ("-RSB-", "]"),
    ("-LCB-", "{"), ("-RCB-", "}"),
)


def decode_fever_title(raw: object) -> str | None:
    """FEVER encodes wiki titles with underscore separators and -LRB-/-RRB- style brackets."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    title = raw
    for token, char in _FEVER_TITLE_SUBSTITUTIONS:
        title = title.replace(token, char)
    title = title.replace("_", " ").strip()
    return title or None


def save_json(name: str, payload: dict | list) -> Path:
    path = RESULTS_DIR / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_json(name: str) -> dict | list:
    return json.loads((RESULTS_DIR / name).read_text(encoding="utf-8"))


def stratified_sample(labels: list[str], n: int, seed: int) -> list[int]:
    """Deterministic stratified sample of ``n`` indices proportional to label frequency."""
    rng = random.Random(seed)
    by_label: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        by_label.setdefault(label, []).append(index)
    total = len(labels)
    chosen: list[int] = []
    for _label, indices in sorted(by_label.items()):
        share = len(indices) / total
        take = min(len(indices), max(1, int(round(n * share))))
        chosen.extend(rng.sample(indices, take))
    chosen = sorted(set(chosen))
    if len(chosen) > n:
        chosen = sorted(rng.sample(chosen, n))
    return chosen


def evidence_page_titles(evidence) -> list[str]:
    """Extract Wikipedia page titles from a FEVER evidence annotation (schema-tolerant)."""
    titles: list[str] = []

    def maybe_add(value) -> None:
        if not isinstance(value, str) or not value:
            return
        if value.startswith("http"):
            value = value.rsplit("/", 1)[-1].replace("_", " ")
        if value and value not in titles:
            titles.append(value)

    def walk(node) -> None:
        if isinstance(node, dict):
            for key in ("page_title", "title", "wikipedia_url", "wiki_url"):
                if key in node:
                    maybe_add(node[key])
            for value in node.values():
                if isinstance(value, (list, dict)):
                    walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                if isinstance(item, (list, tuple, dict)):
                    walk(item)
                elif isinstance(item, str):
                    maybe_add(item)

    walk(evidence)
    return titles


def fetch_wikipedia_page(title: str, lang: str = "en") -> dict | None:
    """Fetch and cache one Wikipedia page's plain-text extract. Returns None on failure."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
    path = CORPUS_DIR / f"{lang}_{safe}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    time.sleep(0.1)
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "redirects": "1",
        "titles": title,
        "format": "json",
        "formatversion": "2",
    }
    try:
        response = httpx.get(
            WIKI_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=30.0
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", [])
    except Exception:  # noqa: BLE001 - eval scripts record, never fabricate
        return None
    if not pages or pages[0].get("missing"):
        return None
    payload = {
        "title": pages[0].get("title", title),
        "pageid": pages[0].get("pageid"),
        "extract": pages[0].get("extract", "") or "",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def fetch_many(
    titles: list[str], workers: int = 8, progress_every: int = 200
) -> tuple[dict[str, str], list[str]]:
    """Fetch many Wikipedia pages concurrently (cached on disk). Returns (pages, missing)."""
    pages: dict[str, str] = {}
    missing: list[str] = []
    if not titles:
        return pages, missing
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for i, (title, data) in enumerate(
            zip(titles, executor.map(fetch_wikipedia_page, titles), strict=True), 1
        ):
            if data and data.get("extract"):
                pages[title] = data["extract"]
            else:
                missing.append(title)
            if progress_every and i % progress_every == 0:
                print(f"  fetched {i}/{len(titles)} pages ({len(pages)} usable)", flush=True)
    return pages, missing


def recall_at_k(gold: set[str], retrieved: list[str], k: int) -> float | None:
    if not gold:
        return None
    return len(gold & set(retrieved[:k])) / len(gold)


def precision_at_k(gold: set[str], retrieved: list[str], k: int) -> float | None:
    top = retrieved[:k]
    if not top:
        return None
    return len(gold & set(top)) / len(top)


def reciprocal_rank(gold: set[str], retrieved: list[str]) -> float:
    for rank, item in enumerate(retrieved):
        if item in gold:
            return 1.0 / (rank + 1)
    return 0.0


def mean(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)
