# Uncertainty and limitations

VerityAI is built around the idea that **honest uncertainty is more useful than a confident
guess**.

## What the scores mean

- **Retrieval relevance** (`rrf_score`, `rerank_score`) — how well a passage matches the *query*.
  A contradicting passage can score high.
- **NLI score** (`nli_score`, `nli_probs`) — the model's output for **one passage-claim pair**.
  It is not the probability that the claim is true.
- **Verdict** (`SUPPORTED` / `REFUTED` / …) — the result of the explicit aggregation rules over
  the retrieved evidence, and nothing more.

## Sources of uncertainty

1. **Coverage** — only the configured permitted sources are queried; the right evidence may not
   have been retrieved (or may not exist publicly).
2. **Recency** — sources change; evidence reflects retrieval time.
3. **Independence** — corroboration is only as strong as the independence of the sources.
4. **Model error** — NLI can misclassify, especially on numeric, temporal and negation-heavy
   claims.
5. **Language** — the benchmark and models are English-first.

## How VerityAI responds

- It **never** forces a verdict: weak or absent evidence yields `INSUFFICIENT_EVIDENCE`, and
  unreachable sources yield `UNABLE_TO_ASSESS`.
- It flags `limited_corroboration` when a verdict rests on a single independent source.
- It lists `sources_queried` and `source_failures` so the user can see what was actually checked.
- It returns the passages themselves, with links, so the user can read the evidence directly.

## What it must not be used for

Do not treat a VerityAI verdict as ground truth, and do not cite it as a source. Read the cited
sources.
