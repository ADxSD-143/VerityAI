# Phase 0 candidate claims (machine-proposed, UNREVIEWED)

`phase0_candidates.csv` holds MACHINE-PROPOSED drafts for human review. They are **not gold
labels** and must not be used to compute held-out metrics until a human has verified every row.

## Columns

- `proposed_claim_type`, `proposed_verdict`, `proposed_handling` — the assistant's proposal only.
- `proposed_verdict` is intentionally **blank** for `OPINION_SUBJECTIVE` / `PREDICTION` /
  `UNCLEAR` rows, because the output contract forbids a true/false verdict for those.
- `ambiguous=yes` marks rows whose correct label is debatable (contested measures, allegation
  handling) and needs adjudication.
- `split` is a suggested `tuning` / `held_out` assignment.

## How to review

1. Open `phase0_e2e_template.csv` (the clean template).
2. For each candidate, copy `claim_text` and — after checking a source — fill `claim_type_gold`,
   `verdict_gold`, `source_urls` / `source_dates`, `reviewer`, `ambiguous`, `rationale`, `split`.
3. Promote only rows you have verified. Keep **>= 60** rows in the `held_out` split.
4. Any row used to justify a threshold change must be moved to the `tuning` split first.

## Fixed rules

- Never use model output as the gold label.
- Opinions and predictions get no true/false verdict; allegations report what is *alleged* versus
  what an official body or court has *proven*.
- Absence of evidence is not falsity; many rows are expected to end as `INSUFFICIENT_EVIDENCE`.

## Known Phase 0 gap

The pipeline cannot yet emit `NOT_VERIFIABLE` or the allegation-specific report (that is Phase 2).
Opinion / prediction / allegation rows are therefore expected to "fail" in Phase 0 — recorded
honestly, not hidden.
