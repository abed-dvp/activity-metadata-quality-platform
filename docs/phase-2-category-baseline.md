# Phase 2 — Category quality baseline

## Objective

Establish an interpretable category-quality baseline before introducing an LLM evaluator.

The baseline answers a deliberately narrow question:

> How much category membership can be recovered from explicit lexical evidence in the real POI metadata?

This is not intended to be the final classifier. It establishes a measurable reference point and produces concrete false-positive and false-negative cases for the next evaluator iteration.

## Why a deterministic baseline comes first

The project follows an eval-driven sequence: define the evaluation set, establish a transparent baseline, inspect failures, and only then introduce more complex semantic reasoning.

A deterministic baseline has three practical advantages:

1. its behavior is auditable;
2. its cost and latency are effectively negligible;
3. its failure modes make it easier to identify where an LLM is actually necessary.

This is consistent with the benchmark decision to separate programmatic/deterministic checks from semantic LLM checks rather than sending every requirement to a general-purpose model.

## Inputs

The phase consumes:

```text
data/processed/category_evaluation.csv
```

created in Phase 1 from the canonical London catalog joined to human annotations.

The ground-truth `is_member` field is used only by the evaluation step and is never used to generate a prediction.

## Baseline logic

For each `(entity, category)` pair, the baseline looks for category-derived terms and optional aliases across:

- POI name;
- source category;
- details;
- review text.

Evidence is weighted by field. Explicit category evidence in a name or source category contributes more than a mention in free-form reviews.

The baseline records both its score and the evidence that triggered the score, so every prediction remains inspectable.

## Outputs

```text
data/processed/category_predictions.csv
data/processed/category_metrics.csv
data/processed/category_failures.csv
data/processed/category_failure_summary.csv
data/processed/phase2_summary.json
```

Metrics are reported per category as well as micro and macro aggregates. The per-category view is primary; aggregate values are convenience summaries only.

## Decision gate

No LLM evaluator should be tuned before the following are reviewed:

1. per-category precision/recall/F1;
2. categories with zero or near-zero recall;
3. the highest-volume false negatives;
4. false positives caused by ambiguous terms;
5. annotation categories whose labels cannot be interpreted reliably from their column names.

The next phase will use those observed failures to define atomic semantic evaluators rather than starting from a generic prompt.
