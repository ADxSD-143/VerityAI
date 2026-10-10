# Experiment 004 — end-to-end on live claims

**Question.** Does the whole pipeline produce sensible statuses on real, live claims?

**Setup.** 8 hand-labelled claims covering supported / refuted / conflicting / insufficient cases,
run through the real pipeline (live Wikipedia + Wikidata + OpenAlex retrieval → hybrid ranking →
NLI → aggregation).

**Command.** `python experiments/eval_e2e.py`

**Results.** 4/8 matched the expected status. Latency 2.0–19.8 s per claim (warm models).

| Claim | Expected | Actual |
|---|---|---|
| The Eiffel Tower is located in Paris. | SUPPORTED | CONFLICTING_EVIDENCE |
| The Great Wall of China is located in Japan. | REFUTED | REFUTED ✓ |
| The capital of Australia is Canberra. | SUPPORTED | SUPPORTED ✓ |
| The capital of Australia is Sydney. | REFUTED | CONFLICTING_EVIDENCE |
| Python was created by Guido van Rossum. | SUPPORTED | SUPPORTED ✓ |
| Mount Everest is the highest mountain above sea level on Earth. | SUPPORTED | SUPPORTED ✓ |
| The Amazon River is the longest river in the world by every measure. | CONFLICTING_EVIDENCE | REFUTED |
| Zorbax-9 was the first spacecraft to land on the Sun. | INSUFFICIENT_EVIDENCE | SUPPORTED |

**Findings.**

1. **Entity contamination** — for the Eiffel Tower and Sydney claims, retrieval pulled a *different
   entity* (Eiffel Tower (Paris, Texas), pages about Sydney) and one passage was judged
   contradictory → `CONFLICTING_EVIDENCE` instead of a single verdict. Retrieval is traceable but
   imprecise.
2. **False positive on a nonsense claim** — "Zorbax-9 … land on the Sun" returned `SUPPORTED` from a
   single passage. `limited_corroboration` was correctly set, but the verdict was still given. This
   is the most serious observed failure mode.

**Limitations.** 8 claims is far too small to estimate accuracy; results are indicative only and not
reproducible (live sources change).

**Decision.** Do **not** tune the aggregation thresholds on this set — that would be fitting to the
test. Document failure mode 2 as a known limitation and keep `limited_corroboration` as the current
mitigation. No code change made on the basis of these 8 examples.

**Artefacts.** `experiments/results/eval_e2e.json`.
