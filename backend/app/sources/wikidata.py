"""Wikidata structured-fact adapter.

Matches claim entity hints to Wikidata items and turns a curated set of properties
into short, citable factual statements (e.g. ``Douglas Adams: date of birth —
1952-03-11.``). These are *original structured facts*, not publisher verdicts.

Uses the public Action API (``wbsearchentities``, ``wbgetentities``) and
``Special:EntityData`` – keyless. Entity-id property values are resolved to English
labels in a single batched call.
"""

from __future__ import annotations

import httpx

from ..core.text import entity_hints
from .base import EvidencePassage, SourceAdapter, SourceResult, now_iso

_PROP_LABELS = {
    "P31": "instance of", "P17": "country", "P27": "country of citizenship",
    "P571": "inception", "P576": "dissolved", "P580": "start time", "P582": "end time",
    "P585": "point in time", "P569": "date of birth", "P570": "date of death",
    "P1082": "population", "P2044": "elevation", "P2043": "length", "P155": "follows",
    "P156": "followed by", "P361": "part of", "P279": "subclass of",
    "P159": "headquarters location", "P276": "location", "P19": "place of birth",
    "P20": "place of death", "P26": "spouse", "P50": "author", "P57": "director",
    "P86": "composer", "P112": "founded by", "P123": "publisher", "P136": "genre",
    "P166": "award received", "P625": "coordinate location", "P6": "head of government",
    "P35": "head of state", "P169": "chief executive officer", "P740": "location of formation",
}


def _fmt_time(raw: str) -> str:
    date = raw.lstrip("+").split("T")[0]
    parts = date.split("-")
    if len(parts) == 3:
        year, month, day = parts
        if month == "00" and day == "00":
            return year
        if day == "00":
            return f"{year}-{month}"
    return date


class WikidataAdapter(SourceAdapter):
    name = "wikidata"
    kind = "evidence"
    access = "Wikidata Action API + Special:EntityData, public, no key"
    rate_limits = "polite use; a handful of requests per claim"

    def __init__(self, *, user_agent: str, timeout: float = 20.0,
                 max_entities: int = 3, max_facts: int = 14) -> None:
        self.endpoint = "https://www.wikidata.org/w/api.php"
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_entities = max_entities
        self.max_facts = max_facts

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    async def search(
        self, claim: str, queries: list[str], client: httpx.AsyncClient
    ) -> SourceResult:
        terms = entity_hints(claim) or queries[:1] or [claim]
        try:
            qids: list[str] = []
            for term in terms[:3]:
                for qid in await self._find_entities(client, term):
                    if qid not in qids:
                        qids.append(qid)
            qids = qids[: self.max_entities]
            if not qids:
                return SourceResult(status="empty", queries=terms, endpoint=self.endpoint)

            entities = [await self._fetch_entity(client, qid) for qid in qids]
            entities = [e for e in entities if e]
            labels = await self._resolve_labels(client, self._collect_refs(entities))
            passages = self._to_passages(entities, labels)
        except Exception as exc:  # noqa: BLE001
            return SourceResult(status="error", error=f"wikidata failed: {exc}",
                                queries=terms, endpoint=self.endpoint)

        return SourceResult(
            passages=passages,
            status="ok" if passages else "empty",
            queries=terms,
            endpoint=self.endpoint,
        )

    async def _find_entities(self, client: httpx.AsyncClient, term: str) -> list[str]:
        params = {
            "action": "wbsearchentities", "search": term, "language": "en",
            "uselang": "en", "limit": "3", "format": "json", "formatversion": "2",
        }
        resp = await client.get(self.endpoint, params=params, headers=self._headers(),
                                timeout=self.timeout)
        resp.raise_for_status()
        return [r["id"] for r in resp.json().get("search", []) if r.get("id")]

    async def _fetch_entity(self, client: httpx.AsyncClient, qid: str) -> dict | None:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        resp = await client.get(url, headers=self._headers(), timeout=self.timeout)
        if resp.status_code != 200:
            return None
        return resp.json().get("entities", {}).get(qid)

    def _collect_refs(self, entities: list[dict]) -> list[str]:
        refs: list[str] = []
        for ent in entities:
            for prop, claims in (ent.get("claims") or {}).items():
                if prop not in _PROP_LABELS:
                    continue
                for claim in claims[:2]:
                    value = (claim.get("mainsnak", {}).get("datavalue") or {}).get("value")
                    if isinstance(value, dict) and value.get("id"):
                        qid = value["id"]
                        if qid not in refs:
                            refs.append(qid)
        return refs[:40]

    async def _resolve_labels(self, client: httpx.AsyncClient, qids: list[str]) -> dict[str, str]:
        if not qids:
            return {}
        params = {
            "action": "wbgetentities", "ids": "|".join(qids), "props": "labels",
            "languages": "en", "format": "json", "formatversion": "2",
        }
        resp = await client.get(self.endpoint, params=params, headers=self._headers(),
                                timeout=self.timeout)
        resp.raise_for_status()
        out: dict[str, str] = {}
        for qid, ent in (resp.json().get("entities") or {}).items():
            label = (ent.get("labels") or {}).get("en", {}).get("value")
            if label:
                out[qid] = label
        return out

    def _render_value(self, snak: dict, labels: dict[str, str]) -> str | None:
        if snak.get("snaktype") != "value":
            return None
        dv = snak.get("datavalue") or {}
        value = dv.get("value")
        dtype = dv.get("type")
        if dtype == "wikibase-entityid" and isinstance(value, dict):
            qid = value.get("id")
            return labels.get(qid, qid)
        if dtype == "time" and isinstance(value, dict):
            return _fmt_time(value.get("time", ""))
        if dtype == "quantity" and isinstance(value, dict):
            return str(value.get("amount", "")).lstrip("+")
        if dtype == "globecoordinate" and isinstance(value, dict):
            return f"{value.get('latitude')}, {value.get('longitude')}"
        if dtype == "monolingualtext" and isinstance(value, dict):
            return value.get("text")
        if isinstance(value, str):
            return value
        return None

    def _to_passages(self, entities: list[dict], labels: dict[str, str]) -> list[EvidencePassage]:
        stamp = now_iso()
        out: list[EvidencePassage] = []
        for ent in entities:
            qid = ent.get("id", "")
            label = (ent.get("labels") or {}).get("en", {}).get("value", qid)
            description = (ent.get("descriptions") or {}).get("en", {}).get("value")
            url = f"https://www.wikidata.org/wiki/{qid}"
            if description:
                out.append(EvidencePassage(
                    text=f"{label} — {description}.", source=self.name, title=label,
                    url=url, publisher="wikidata.org", page_id=qid, retrieved_at=stamp,
                    meta={"property": "description"},
                ))
            for prop, claims in (ent.get("claims") or {}).items():
                if prop not in _PROP_LABELS:
                    continue
                rendered = self._render_value(claims[0].get("mainsnak", {}), labels)
                if not rendered:
                    continue
                out.append(EvidencePassage(
                    text=f"{label}: {_PROP_LABELS[prop]} — {rendered}.",
                    source=self.name, title=label, url=url, publisher="wikidata.org",
                    page_id=qid, retrieved_at=stamp, meta={"property": prop},
                ))
                if len(out) >= self.max_facts:
                    return out
        return out
