# Phase 1 — Real-data ingestion and evaluation foundation

## Objective

Establish a reproducible real-world tourism data layer before introducing semantic evaluators or synthetic enrichment.

The first source is the **Enriched Tourism Dataset London (POIs)**. It contains a curated London POI catalog and a separate set of human-created multi-label category annotations. The source is distributed under **CC BY 4.0**.

## Why this source is used first

The London dataset provides two assets that are unusually useful together:

1. real tourism entities with names, addresses, coordinates, descriptive information and review-derived text;
2. independently human-annotated category labels that can be treated as external ground truth.

This makes it possible to establish an evaluation pipeline on real tourism data before adding marketplace-specific fields that are not present in the open dataset.

## Data sequence

```text
Official London source
        |
        +-- London.csv -------------------+
        |                                 |
        +-- London_annotated.csv           |
                  |                        |
                  v                        v
             source profiling        canonical mapping
                  |                        |
                  +-----------+------------+
                              v
                    join-coverage validation
                              |
                              v
                    category evaluation table
                              |
                              v
                  semantic evaluator (next phase)
```

## Acceptance gates

Semantic evaluation must not start until the following are reported:

- source row counts;
- available columns;
- null rates;
- duplicate rates;
- coordinate validity;
- detected annotation categories;
- number of positive labels per category;
- join coverage between the catalog and human annotations.

A low join-coverage result is treated as a data-integration defect, not as a model-quality problem.

## Scope boundary

The source is POI-oriented rather than a complete bookable-activity catalog. Marketplace-specific fields such as pickup configuration, private/shared options, guide type and accessibility claims are therefore not fabricated in this phase.

Those dimensions will be introduced later through controlled enrichment after the real-data category and location pipeline is stable. Keeping the phases separate prevents synthetic assumptions from contaminating the baseline evaluation.
