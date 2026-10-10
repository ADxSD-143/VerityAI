# Experiment 002 — NLI model comparison (base vs small)

**Question.** Should the default NLI model be `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` or the
smaller `cross-encoder/nli-deberta-v3-small`?

**Hypothesis.** The base model is more accurate; the small model is faster and may be a better
fit for a constrained host.

**Setup.** The same 500-claim sample. Premise = BM25-selected sentence from the claim's gold pages
(SUPPORTS/REFUTES) or a random non-gold sentence (`NOT ENOUGH INFO`). Expected mapping
SUPPORTS→entailment, REFUTES→contradiction, NEI→neutral. Metrics: accuracy, macro-F1, per-class
P/R/F1, confusion matrix, mean latency.

**Commands.**

```bash
python experiments/eval_nli.py --limit 500 --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
python experiments/eval_nli.py --limit 500 --model cross-encoder/nli-deberta-v3-small --out eval_nli_small.json
```

**Results** (n = 493).

| Model | Accuracy | Macro-F1 | Latency/pair | Label order (from config) |
|---|---|---|---|---|
| `DeBERTa-v3-base-mnli-fever-anli` | **0.675** | **0.671** | 90.5 ms | `0=entailment, 1=neutral, 2=contradiction` |
| `nli-deberta-v3-small` | 0.448 | 0.458 | 98.0 ms | `0=contradiction, 1=entailment, 2=neutral` |

Base per-class F1: entailment 0.624, neutral 0.688, contradiction 0.701 (very high entailment
precision 0.907, low recall 0.476).

**Interpretation.** The base model is clearly better on this benchmark, and the small model was
*not* faster on this CPU. Critically, the two models use **different label orders** — reading the
map from the loaded config (and rejecting unresolvable maps) is mandatory, not cosmetic.

**Limitations.** The premise is a BM25-selected sentence from a reconstructed page, so many
"errors" are cases where the retrieved sentence genuinely does not entail the claim and *neutral* is
correct. These are not FEVER leaderboard numbers.

**Decision.** Keep the base model as the default. Document the small model as a **fallback** for a
host that cannot fit the base model (~380 MB), not as an equivalent.

**Artefacts.** `experiments/results/eval_nli.json`, `experiments/results/eval_nli_small.json`.
