# Unified Quality Impact Score

## Purpose

This stage combines currently available **Category Quality** and **Location Quality** signals into one review-prioritization layer.

The score is deliberately called an **impact score**, not a business KPI.

```text
0   = no observed issue in evaluated domains
100 = highest configured review impact
```

Higher means **more urgent quality review**.

## Important limitation

The weights are heuristic prioritization weights.

They are **not** calibrated estimates of:

- conversion loss;
- revenue loss;
- cancellation probability;
- customer-support cost;
- supplier value.

Those claims would require downstream marketplace outcome data and causal/experimental validation.

## Domain weights

Maximum observed contribution:

- Location Quality: 55
- Category Quality: 45

### Location

| Route | Impact |
|---|---:|
| PASS | 0 |
| BOUNDARY_REVIEW | 15 |
| GEOCODER_UNRESOLVED_REVIEW | 20 |
| ADDRESS_QUALITY_REVIEW | 25 |
| ADDRESS_OR_GEOCODER_REVIEW | 35 |
| COORDINATE_MISMATCH_CANDIDATE | 55 |

No route automatically changes supplier metadata.

### Category

For evaluation data, the semantic evaluator is compared with the existing public membership reference.

- confident agreement: 0–10 depending on confidence;
- uncertain/provider failure: 20;
- disagreement: 25–45 depending on confidence.

In a production marketplace this reference would be the current catalog/supplier category assignment, **not evaluation gold labels**.

## Coverage

A score can only be called `full` when both Category and Location were evaluated.

If Category evidence is unavailable:

```text
score_status = partial
domain_coverage = 0.5
```

Partial and full scores should not be ranked directly against one another.

## Real-data overlap

The score uses real row-level artifacts from the independent Phase 5 category holdouts.

Among the 30 location-diagnostic entities:

- 13 unique entities have at least one Category holdout evaluation;
- 16 category-evaluation rows overlap in total;
- categories represented: museum and nature.

The category overlap evidence is cached in:

`reports/impact/category_overlap_evidence.csv`

This avoids rerunning Gemini and adds no new model cost.

## Governance

- automatic action: disabled;
- production routing: disabled;
- score weights: explicit and auditable;
- missing-domain evidence: never treated as good quality;
- score is for review prioritization only.
