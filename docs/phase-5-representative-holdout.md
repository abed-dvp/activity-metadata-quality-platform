# Phase 5 — Representative holdout validation

## Purpose

Phase 3 calibration was intentionally stratified around deterministic failure modes. It was useful for evaluator development but not representative of natural catalog prevalence.

Phase 5 therefore excludes **all 240 Phase 3 calibration entities** and validates the same frozen evaluator on residual data.

## Holdout design

Two views are created from the residual museum population:

1. **Representative residual sample** — 600 random rows, fixed seed, used for operational precision / accuracy / coverage and confidence-routing analysis.
2. **Positive sensitivity diagnostic** — every remaining public-label-positive museum row, used to inspect positive recall because museum prevalence is low.

The API evaluates the **union once**, so rows appearing in both views do not create duplicate inference cost.

## Why two views are required

After excluding the Phase 3 calibration set, the residual museum prevalence is only about 1.5%.

A representative sample alone therefore contains very few positives and produces an unstable recall estimate. Evaluating all remaining positives provides a sensitivity diagnostic without distorting the representative sample used for operational routing.

## Evaluation reference caveat

Phase 4 showed strong evidence that some public labels conflict with the explicit project ontology.

Accordingly:

- holdout metrics are reported against the public annotation reference;
- they are not described as final human-gold accuracy;
- disagreements should feed future human adjudication.

## Cost guard

Phase 5 uses `gemini-3.8-flash` with low thinking.

The successful Phase 3 run cost roughly $0.19 for 240 rows. The Phase 5 union is expected to remain around 600–631 rows, implying roughly $0.5 under the same token profile.

The workflow must not be expanded beyond this design without re-estimating cost.
