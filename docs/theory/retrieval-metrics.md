# Retrieval metrics

**Recall@k.** Fraction of the gold (relevant) items that appear in the top *k* retrieved items.

$$\text{Recall@}k = \frac{|\,\text{gold} \cap \text{top-}k\,|}{|\text{gold}|}$$

In our page-level evaluation, gold is the set of evidence pages for the claim.

**Precision@k.** Fraction of the top *k* retrieved items that are relevant:

$$\text{Precision@}k = \frac{|\,\text{gold} \cap \text{top-}k\,|}{k}$$

When a claim has fewer gold pages than *k*, precision is inherently bounded below 1; we report
the value our annotations support and note the bound.

**Mean Reciprocal Rank (MRR).** Average of $1/\text{rank}$ of the first relevant item:

$$\text{MRR} = \frac{1}{|Q|}\sum_{q \in Q} \frac{1}{\text{rank}_q}$$

where $1/\text{rank}_q = 0$ if no relevant item is retrieved.

**Evidence coverage.** The fraction of evaluated claims for which at least one gold page was
present in the corpus — it bounds how much of the sample is actually measurable.

**Missing / unanswerable handling.** Claims with no gold evidence page in the corpus (e.g. the page
could not be fetched) are excluded from retrieval metrics and counted in
`skipped_no_gold_in_corpus`, rather than being scored as a miss.

**In VerityAI.** `experiments/_common.py` and `experiments/eval_retrieval.py`.

**Limitations.** Page-level relevance is coarser than sentence-level; results are specific to the
reconstructed corpus (see `docs/DATASETS.md`).
