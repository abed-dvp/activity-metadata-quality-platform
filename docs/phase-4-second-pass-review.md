# Phase 4 — Second-pass assisted review

A second evidence-first review was performed on the 17 first-pass candidate-gold cases.

## Result

- 16 / 17 decisions were stable (**94.12%**).
- 1 case changed: **Red Gate Gallery**.
- Red Gate Gallery moved from `not_member` to `ambiguous` because the available evidence does not establish whether it is primarily an institutional gallery, a commercial gallery, or a generic event venue.
- Final assisted candidate set: **16 cases**.
- Total ambiguous cases after the second pass: **12**.

## Governance

These labels remain:

```text
reviewer_type = assistant_second_pass
review_status = SECOND_PASS_ASSISTED_REVIEW
human_gold_status = NOT_FINAL_HUMAN_GOLD
```

They are useful as adjudicated candidates and for ontology analysis, but they are not represented as independent human gold.

## Decision

Proceed to an **independent representative holdout** that excludes all 240 Phase 3 calibration cases.

The holdout will report two views:

1. a representative random residual sample for operational precision / coverage / routing;
2. all remaining public-label-positive museum cases as a sensitivity diagnostic.

This avoids reusing the calibration set while still providing enough positive cases to inspect recall.
