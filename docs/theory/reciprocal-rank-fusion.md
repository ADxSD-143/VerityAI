# Reciprocal Rank Fusion

**Intuition.** Different retrievers produce scores on incomparable scales (BM25 is unbounded,
cosine is in [0, 1]). Instead of trying to calibrate them, RRF combines retrievers by the
**ranks** they assign: a document that both rank highly wins.

**Formula.** For a set of rankers, with $k$ a smoothing constant (60 is conventional):

$$\text{RRF}(d) = \sum_{i} \frac{w_i}{k + \text{rank}_i(d)}$$

where $\text{rank}_i(d)$ is the (0-based) rank of document $d$ in ranker $i$.

**Example.** If BM25 places passage A at rank 1 and BGE places it at rank 2, while passage B is
rank 1 for BGE but rank 20 for BM25, A accumulates more RRF score and rises to the top — the
consensus passages win.

**In VerityAI.** `backend/app/retrieval/fusion.py::rrf_fuse` with $k=60$, combining the BM25 and
BGE orderings in `backend/app/retrieval/pipeline.py`. Near-duplicate passages are removed after
fusion so syndicated copies do not dominate.

**Limitations.** RRF ignores score magnitudes (a document ranked 1st by a mile and one barely 1st
are treated the same). It is a robust, parameter-light default — but "high RRF" means *relevant to
the query*, never *true*.
