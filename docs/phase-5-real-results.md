# Phase 5 — Representative museum holdout results

## Executive summary

Phase 5 validates the frozen museum evaluator on data that is independent of the 240-row Phase 3 calibration set.

The residual museum population contains 2,024 entities after excluding all 240 calibration entities. Museum prevalence in the residual public labels is only **1.53%**, so the evaluation uses two views:

1. a fixed-seed 600-row representative sample for operational routing;
2. all 31 remaining public-label-positive rows as a positive-sensitivity diagnostic.

The union contains 623 unique rows and is evaluated once.

## Representative holdout

On the 600-row representative sample:

- public-label positives: 8
- public-label negatives: 592
- decided rows: 572
- coverage: **95.33%**
- abstention: **4.67%**
- public-reference TP: 8
- public-reference FP: 9
- public-reference FN: 0
- public-reference TN: 555

Against the public labels, decided-case precision is **47.06%**, recall **100%**, and F1 **64.0%**.

This low positive precision must not be interpreted as a simple semantic-model failure. The nine apparent false positives are strongly concentrated in entities that satisfy the project's explicit museum/heritage ontology but are labelled non-museum in the public source.

Examples include:

- Carlyle's House
- Queen's House
- Cutty Sark
- The Courtauld Institute of Art
- Kew Palace
- Zabludowicz Collection
- Whitechapel Gallery
- The House Mill
- PM Gallery & House

Several are clearly visitor-oriented heritage sites, public collections, or interpretive institutions. They should enter adjudication rather than automatically becoming prompt regressions.

## Positive sensitivity diagnostic

All 31 residual public-label-positive rows were evaluated:

- 28 → `member`
- 2 → `not_member`
- 1 → `uncertain`

Strict member rate: **90.32%**.

Member-or-review-safe rate: **93.55%**.

The two `not_member` cases are:

- The Graffiti Life Gallery
- Stolenspace Gallery

Both appear consistent with the project's exclusion of commercial/contemporary galleries rather than museum institutions.

The uncertain positive is:

- National Gallery Shop

The entity name indicates a retail shop while the review text describes the parent gallery, making this a parent/entity-resolution ambiguity rather than a clean semantic miss.

## Operational provider fallback

One row, `The Electric Lounge`, produced no usable Gemini text after retries. The provider now records:

```text
semantic_decision = uncertain
provider_error = EMPTY_RESPONSE
```

and routes the case to human review instead of failing the batch.

This is intentional fail-safe behavior. Infrastructure/model-output failures are not silently converted into binary category decisions.

## Threshold validation

The representative holdout produces:

| Threshold | Auto coverage | Auto accuracy vs public reference | Auto errors |
|---:|---:|---:|---:|
| 0.90 | 90.17% | 98.71% | 7 |
| 0.95 | 86.00% | 99.03% | 5 |
| **0.98** | **60.17%** | **100.00%** | **0** |
| 0.99 | 55.50% | 100.00% | 0 |

`0.98` is therefore the current **candidate conservative threshold**, not a production threshold.

At 0.98:

- 361 / 600 cases would be auto-routed;
- 239 / 600 would go to review;
- there are zero errors against the public-label reference in the representative sample;
- only 6 of the 8 representative public-positive rows are auto-routed; the other 2 remain reviewable rather than incorrectly auto-rejected.

## Comparison with deterministic baseline

On the same 600 representative rows, the deterministic lexical baseline produces:

- TP: 8
- FP: 16
- FN: 0
- TN: 576
- precision: **33.33%**
- recall: **100%**
- F1: **50.0%**

The semantic evaluator therefore reduces public-reference false positives from 16 to 9 before confidence routing, while maintaining recall on this sample.

More importantly, confidence routing at 0.98 creates a high-precision auto lane and sends the uncertain boundary to review.

## Cost

The successful Phase 5 holdout used:

- input tokens: **335,791**
- output + thinking tokens: **62,106**
- estimated standard Gemini 3.8 Flash cost in October 2026: **$0.485**

The cost estimate uses the then-current standard rates of $0.75 / 1M input tokens and $3.75 / 1M output tokens including thinking.

The API workflow is now explicit-trigger only for semantic calibration, reducing accidental inference spend.

## Decision

The evaluator is strong enough to support a conservative routing architecture, but production activation remains disabled.

Current state:

```text
confidence >= 0.98
    → candidate auto-route lane

confidence < 0.98
or uncertain
or provider_error
    → HUMAN_REVIEW
```

This policy is still **offline / pre-production** because the public reference is demonstrably noisy and the 16 stable assisted-adjudication cases are not independent human gold.

## Next gate

Before `production_enabled=true`:

1. human-adjudicate the holdout disagreements and threshold-boundary cases;
2. separate public-label errors from true model errors;
3. establish a final human regression set;
4. define asymmetric business costs for false positive vs false negative category actions;
5. validate member and not-member thresholds independently.
