# Cosine similarity

**Intuition.** The cosine of the angle between two vectors measures how aligned they are,
ignoring their magnitudes. For normalized vectors it is just the dot product.

**Formula.**

$$\cos(a, b) = \frac{a \cdot b}{\lVert a \rVert\,\lVert b \rVert}$$

Range: $[-1, 1]$ for general vectors, $[0, 1]$ for non-negative ones.

**Example.** Two passages about the same event score near 1; unrelated ones near 0.

**In VerityAI.** Because `BGE` embeddings are normalized (`normalize_embeddings=True`), the
dense ranker computes `matrix @ query_vec` — a dot product — in
`backend/app/retrieval/dense.py`.

**Limitations.** Cosine similarity measures *topical/lexical-semantic similarity*, not truth.
A passage that is on-topic but contradicts the claim can still have high cosine similarity. That
is precisely why NLI (not similarity) decides support/contradiction, and why similarity is never
presented as a truth score.
