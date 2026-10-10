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
| strong support only | `SUPPORTED` |
| strong contradiction only | `REFUTED` |
| all sources unreachable | `UNABLE_TO_ASSESS` |

A `SUPPORTED`/`REFUTED` result resting on fewer than two independent sources is flagged
`limited_corroboration = true` and says so in the explanation.

**Example.** Two identical sentences mirrored on two domains → one group → not enough for
unqualified corroboration. Two different pages that each independently entail the claim → two
groups.

**Limitations.** Thresholds are principled defaults, not fitted on the evaluation sample, so they
are conservative rather than optimal. Aggregation is intentionally interpretable and rule-based
rather than a learned credibility score. VerityAI does **not** assign publisher credibility
scores.
