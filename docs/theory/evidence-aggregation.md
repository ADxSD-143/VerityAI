# Evidence aggregation and source independence

**Intuition.** One sentence from one page is weak evidence. Corroboration is stronger — but only
if the sources are genuinely independent. Two outlets republishing the same wire story are **one**
source.

**Independence.** `backend/app/analysis/independence.py` groups passages by document key
(page id, else canonical URL), then merges groups whose text is a near-duplicate (5-gram Jaccard
≥ 0.8). Aggregation counts **groups**, not passages.

**Aggregation rules.** `backend/app/analysis/aggregation.py`. A passage is a *strong* supporter /
contradictor when its NLI argmax label is entailment / contradiction **and** the score is ≥ `tau`
(default 0.5).

| Situation | Status |
|---|---|
| no strong evidence either way | `INSUFFICIENT_EVIDENCE` |
| strong support **and** strong contradiction | `CONFLICTING_EVIDENCE` |
| strong support only, corroborated (≥2 independent sources) | `SUPPORTED` |
| strong support only, single source with best score ≥ `tau_single` | `SUPPORTED` |
| strong support only, single source with best score < `tau_single` | `INSUFFICIENT_EVIDENCE` |
| strong contradiction only | `REFUTED` (same single-source rule) |
| all sources unreachable | `UNABLE_TO_ASSESS` |

**Single-source safeguard.** A verdict resting on one independent source must clear a *higher* bar,
`tau_single` (default 0.75, `VERITY_TAU_NLI_SINGLE_SOURCE`) than a corroborated one. A lone passage
scoring between `tau` and `tau_single` is too weak to carry a verdict and returns
`INSUFFICIENT_EVIDENCE` instead of `SUPPORTED`/`REFUTED`. This trades recall for precision — a
genuine claim supported by a single weak source is reported as insufficient rather than
`SUPPORTED`. When a lone source does clear `tau_single`, the result is flagged
`limited_corroboration = true` and says so in the explanation. Corroborated verdicts and
`CONFLICTING_EVIDENCE` are unaffected by `tau_single`.

**Example.** Two identical sentences mirrored on two domains → one group → not enough for
unqualified corroboration. Two different pages that each independently entail the claim → two
groups.

**Limitations.** Thresholds are principled defaults, not fitted on the evaluation sample, so they
are conservative rather than optimal. Aggregation is intentionally interpretable and rule-based
rather than a learned credibility score. VerityAI does **not** assign publisher credibility
scores.
