# Phase 6 — Holdout adjudication and asymmetric routing

## Executive summary

Phase 6 tests whether `AUTO_MEMBER` and `AUTO_NOT_MEMBER` should use different confidence thresholds.

The main result is intentionally conservative:

```text
member threshold     = 0.98
not-member threshold = 0.98
production_enabled   = false
```

The two lanes are now implemented and validated independently even though they currently converge to the same candidate value.

## Holdout disagreement review

Thirteen high-value Phase 5 cases were reviewed from source evidence and the explicit museum ontology:

- 9 apparent false-positive `member` decisions in the representative sample;
- 2 `not_member` decisions among the residual public-positive diagnostic;
- 1 public-positive `uncertain` entity-boundary case;
- 1 provider-error abstention.

The assisted review indicates:

- 10 probable public-label errors;
- 1 ontology-boundary mismatch;
- 1 entity-boundary error;
- 1 provider error that was correctly routed to review.

These remain **assisted candidates**, not independent human gold.

## Member lane

Against the public reference:

| Threshold | Auto member | Public-reference errors |
|---:|---:|---:|
| 0.90 | 15 | 7 |
| 0.95 | 13 | 5 |
| **0.98** | **6** | **0** |
| 0.99 | 1 | 0 |

The nine apparent lower-threshold errors are all resolved as member or ontology-compatible in the assisted review. This strongly suggests public-label noise, but it is not sufficient governance evidence to lower the production threshold.

Therefore 0.98 remains the candidate `AUTO_MEMBER` threshold.

## Not-member lane

The representative sample contains no public-reference false negatives in the not-member lane, even at lower thresholds.

However, the all-positive sensitivity diagnostic contains:

- The Graffiti Life Gallery — `not_member`, confidence 0.85
- Stolenspace Gallery — `not_member`, confidence 0.95

The assisted review agrees with Gemini that both are excluded commercial/contemporary galleries. Nevertheless, they are public-positive labels and have not been independently human-adjudicated.

A safety constraint therefore requires that no known public-positive sensitivity case be auto-rejected.

The first threshold satisfying that condition is **0.98**.

## Why cost-only optimization is not enough

Three normalized cost profiles were tested:

- balanced;
- precision-first;
- discovery-protection.

These are sensitivity units, **not euros**.

All three unconstrained profiles prefer approximately:

```text
member = 0.98
not_member = 0.80
```

because a low not-member threshold dramatically reduces review volume.

But that policy auto-rejects two public-positive cases.

The architecture therefore applies:

```text
cost optimization
      ↓
subject to safety constraints
      ↓
candidate routing policy
```

not:

```text
minimize synthetic cost → ship threshold
```

## Candidate policy

```text
provider_error
    → HUMAN_REVIEW

uncertain
    → HUMAN_REVIEW

member AND confidence >= 0.98
    → candidate AUTO_MEMBER

not_member AND confidence >= 0.98
    → candidate AUTO_NOT_MEMBER

everything else
    → HUMAN_REVIEW
```

This is still pre-production.

## What Phase 6 establishes

1. Member and not-member lanes are technically independent.
2. Their risk is evaluated using different evidence:
   - member lane: representative precision;
   - not-member lane: representative negatives plus all-positive sensitivity coverage.
3. Pure cost optimization is subordinate to a safety gate.
4. Provider failures are explicit review cases.
5. Public annotations are treated as a noisy reference rather than unquestioned ground truth.

## Next gate

The next useful step is **category expansion**, not more museum prompt tuning.

The framework should be applied to a category with a different failure shape, such as:

- `nature` — implicit semantic membership;
- `walk` — contextual activity inference;
- `drink` / `nightlife` — overlapping multi-label semantics.

Before any category is allowed to auto-route in production, it must independently pass:

1. real-data baseline;
2. semantic calibration;
3. disagreement review;
4. representative holdout;
5. lane-specific threshold validation.
