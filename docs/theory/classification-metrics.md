# Classification metrics

For the three-class NLI evaluation we report:

**Accuracy.** Fraction of predictions that equal the label:

$$\text{Accuracy} = \frac{\text{correct}}{\text{total}}$$

Accuracy hides class imbalance, so we also report:

**Precision / Recall / F1 per class.** For class $c$,

$$\text{Precision}_c = \frac{TP_c}{TP_c + FP_c}, \quad
\text{Recall}_c = \frac{TP_c}{TP_c + FN_c}, \quad
F1_c = \frac{2\,\text{Precision}_c\,\text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$

**Macro-F1.** The unweighted mean of per-class F1 — it treats all three classes equally, so a
model that ignores `neutral` cannot hide behind the majority class.

**Confusion matrix.** Rows are true labels, columns are predicted labels; it shows *which*
confusions dominate (typically neutral ↔ entailment).

**In VerityAI.** `experiments/eval_nli.py` (scikit-learn metrics), with the label mapping taken
from the model config.

**Limitations.** The premise is a BM25-selected sentence from a reconstructed page rather than the
frozen FEVER gold sentence (see `docs/EVALUATION.md`), so the numbers are indicative of NLI
quality under our construction, not a leaderboard score.
