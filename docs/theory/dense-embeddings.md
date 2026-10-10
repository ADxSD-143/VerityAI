# Dense embeddings

**Intuition.** A neural encoder maps a piece of text to a fixed-length vector so that texts
with similar meaning land near each other, even when they share few words.

**How it is produced.** `BAAI/bge-small-en-v1.5` is a BERT-family encoder trained so that a
query and its relevant passage are close. Following the model card, retrieval **queries** are
prefixed with `"Represent this sentence for searching relevant passages: "` while **passages**
are encoded plain. Outputs are L2-normalized:

$$\hat{v} = \frac{v}{\lVert v \rVert_2}$$

**Example.** "The city of light" and "Paris" get nearby vectors even with no shared tokens.

**In VerityAI.** `backend/app/retrieval/dense.py` wraps `sentence-transformers`. Embeddings are
cached in memory and on disk keyed by `sha256(model_id + text)`, so an unchanged passage is never
re-embedded. The dense arm is fused with BM25 via RRF.

**Limitations.** Embedding a whole corpus costs CPU time; dense models can miss exact numbers or
names — hence the BM25 arm. If the model cannot load, VerityAI degrades to BM25-only and says so.
