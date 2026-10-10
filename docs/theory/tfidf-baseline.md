# TF-IDF (evaluation baseline)

**Intuition.** Weight a term by how often it appears in a document (TF) times how rare it is
across the corpus (IDF). It is a bag-of-words measure: no word order, no semantics.

**Formula.**

$$\text{tfidf}(t, d) = f(t, d)\cdot \log\frac{N}{|\{d' : t \in d'\}|}$$

Documents and queries are then compared with cosine similarity.

**Example.** "capital" is common in a corpus of country articles, so its IDF is low; "Timbuktu"
is rare, so its IDF is high.

**In VerityAI.** TF-IDF appears **only** as an evaluation baseline in
`experiments/eval_retrieval.py` (via scikit-learn). It is deliberately **not** in the runtime
retrieval path. This is a deliberate design decision: the product must not be a TF-IDF-only
system.

**Limitations.** No synonymy or paraphrase handling; that is exactly what the dense retriever
adds. Reported only for comparison.
