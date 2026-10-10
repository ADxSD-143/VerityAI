# Experiment 003 — FEVER corpus reconstruction

**Question.** Can the retrieval benchmark use the FEVER corpus without downloading the multi-GB
`wiki_pages` dump?

**Setup / findings.**

- `fever` `v1.0` has **no `validation` split**; the development split is `labelled_dev` and it needs
  `trust_remote_code=True`.
- `labelled_dev` is stored **flattened**: one row per evidence annotation (37,566 rows for 19,998
  unique claim ids), with scalar `evidence_wiki_url` / `evidence_sentence_id` columns and
  `-LRB-`/`-RRB-`-encoded titles.
- `wiki_pages` is ~5.4M pages / several GB, which is out of scope for a no-cost, small-disk setup.

**Approach.** Group the flattened rows back into claims, decode titles, and **reconstruct** the
corpus from live Wikipedia for the union of gold evidence page titles, plus a deterministic sample
of distractor pages drawn from other claims' evidence pages. Pages are cached under
`data/fever_corpus/` (one JSON file per page).

**Result.** 500 claims → 333 with gold evidence → 367 gold pages; + 800 distractors (seed 42) →
**1161-page corpus**, 6 titles unavailable. 170 claims were excluded from retrieval metrics because
they had no gold page in the corpus (167 `NOT ENOUGH INFO` claims have no evidence pages at all).

**Limitations (documented, not hidden).**

- Relevance is **page-level**, not sentence-level.
- Page text is **current Wikipedia**, not the frozen FEVER dump, so the annotated sentences may no
  longer exist verbatim — a large part of the low NLI entailment recall in experiment 002.
- Corpus size (1161) is far smaller than the real FEVER corpus; absolute Recall@5 is optimistic.

**Decision.** Accept and document the deviation rather than download several GB. Anyone reproducing
this must see the limitation, so it is stated in `docs/DATASETS.md`, `docs/EVALUATION.md` and the
results files.
