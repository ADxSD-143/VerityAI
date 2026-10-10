# Natural Language Inference (NLI)

**Intuition.** NLI asks: given a **premise** and a **hypothesis**, does the premise entail the
hypothesis, contradict it, or neither?

- **entailment** — the premise supports the hypothesis.
- **contradiction** — the premise conflicts with the hypothesis.
- **neutral** — the premise does not settle the question.

**Model.** `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` — a DeBERTa-v3 encoder fine-tuned on
MNLI, FEVER and ANLI. VerityAI uses `premise = evidence passage`, `hypothesis = claim`.

**Example.**
- premise *"Paris is the capital and largest city of France."*, hypothesis *"The Eiffel Tower is
  in Paris."* → likely **neutral** (the premise is about Paris but does not mention the tower).
- premise *"The Great Wall of China is in China."*, hypothesis *"The Great Wall is in Japan."* →
  **contradiction**.

**Labels are read, never assumed.** The class order comes from the loaded `config.id2label`
(`backend/app/analysis/nli.py::_resolve_label_map`) and is validated against the three canonical
labels; an unresolvable mapping raises instead of silently mis-labelling. `test_nli_labels.py`
covers this.

**In VerityAI.** `backend/app/analysis/nli.py`. The output is `nli_label`, `nli_score` and the
full distribution `nli_probs`.

**Limitations.** NLI scores are **not** probabilities that a claim is true. They describe one
passage-claim pair, at one moment, from one source. Neutral is common and legitimate: absence of
evidence is not evidence of absence.
