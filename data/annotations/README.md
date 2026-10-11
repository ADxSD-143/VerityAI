# Phase 0 end-to-end annotation set

phase0_e2e_template.csv is a blank annotation template for a minimum 60-claim held-out set.
Blank fields are intentional. No gold claim types or verdicts have been fabricated.

Required claim_type_gold values: CHECKABLE_FACT, ALLEGATION, OPINION_SUBJECTIVE, PREDICTION, UNCLEAR.

Required verdict_gold values: SUPPORTED, REFUTED, CONFLICTING_EVIDENCE, INSUFFICIENT_EVIDENCE,
UNABLE_TO_ASSESS, NOT_VERIFIABLE, or NOT_APPLICABLE for subjective opinions.

For source_urls and source_dates, separate multiple values with semicolons. Prefer primary or
authoritative sources where appropriate. Mark ambiguous as yes/no and explain disputed
interpretations in rationale. Keep split=held_out fixed. Any example used to change a threshold or
fix a known failure must be moved to a separate tuning set before that change is evaluated.

Include checkable facts across supported/refuted/conflicting/insufficient outcomes, plus opinions,
allegations, predictions and unclear inputs. Allegations about real people must distinguish an
allegation from an official finding; do not mark an accusation true merely because it was reported.
Have a human reviewer verify every gold label and flag ambiguous cases for adjudication.

Do not compute held-out metrics until at least 60 rows contain reviewed claim text and gold labels.
Never use model output as the gold label.

## Validation tooling

Machine-proposed drafts live in `phase0_candidates.csv` (see `phase0_candidates.md`); they are **not**
gold. Validate any annotation file before computing metrics:

    python experiments/annotation_tools.py --path data/annotations/phase0_candidates.csv --schema draft
    python experiments/annotation_tools.py --path data/annotations/phase0_e2e_template.csv --schema gold

The validator checks required columns, claim-type/verdict enums, duplicate case ids and claim texts,
and near-duplicate claim leakage across the tuning/held-out split (script-agnostic character
n-grams). In `gold` mode it errors until at least 60 held-out rows are reviewed. It never fills
labels; unreviewed rows are excluded, never guessed.
