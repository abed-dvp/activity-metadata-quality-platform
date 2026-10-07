# Category expansion — Nature

## Why nature is the second semantic category

The deterministic baseline for `nature` is almost non-functional:

- human positives: 632 / 2,264
- deterministic predicted positives: 3
- precision: 100%
- recall: **0.47%**
- F1: **0.94%**

This is a different failure shape from `museum`.

`museum` exposed adjacent-category boundary problems. `nature` tests **implicit semantic membership**: a park, garden, reserve, woodland, or large green visitor space may clearly be a nature experience without containing the word "nature".

## Evaluation sequence

```text
real London data
  → deterministic baseline
  → 240-row failure-aware Gemini calibration
  → independent residual holdout
  → 600-row representative sample
  → all remaining positive diagnostic
  → confidence threshold sweep
```

All 240 calibration entities are excluded from the holdout.

## Ontology

The existing project ontology defines nature as:

> A place where experiencing natural or green outdoor environments is a primary visitor use.

Included examples:

- parks
- gardens
- woods
- nature reserves
- substantial green spaces

Excluded examples:

- indoor venues
- purely built heritage without meaningful nature experience

## Cost guard

The workflow uses `gemini-3.8-flash` with low thinking.

Based on measured museum token usage, the full nature calibration + holdout is expected to remain well below the user's €5 execution ceiling. If the total token profile materially exceeds that estimate, the workflow output is reviewed before any additional inference is run.

## Success gate

Nature is considered a successful category expansion if it demonstrates:

1. a material recall improvement over the 0.47% deterministic baseline;
2. useful abstention rather than forced classification on weak evidence;
3. stable behavior on an independent holdout;
4. a defensible confidence-routing threshold;
5. failure modes that can be represented in the existing review/adjudication framework.
