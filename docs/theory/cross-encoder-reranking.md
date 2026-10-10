# Cross-encoder reranking

**Intuition.** A bi-encoder (dense retrieval) encodes query and document separately, which is
fast but coarse. A **cross-encoder** reads the query and document **together** and outputs a
relevance score; it is much more accurate but must be run per pair, so it is only affordable on a
small candidate pool.

**Method.** `cross-encoder/ms-marco-MiniLM-L-6-v2` takes `(query, passage)` as one input and
returns a relevance score from its regression head.

**Example.** The hybrid retriever returns 30 candidates; the cross-encoder rescores them, and the
truly on-point passages move to the top.

**In VerityAI.** `backend/app/retrieval/rerank.py`, applied only to the top pool
(`rerank_pool=30`) in the pipeline. It is **off by default** and enabled only if the evaluation
shows a worthwhile gain — see `docs/EVALUATION.md`.

**Limitations.** N× slower than bi-encoder scoring; its score is a *relevance* score, not a truth
or entailment score, and it is reported as `rerank_score`, separate from NLI.
