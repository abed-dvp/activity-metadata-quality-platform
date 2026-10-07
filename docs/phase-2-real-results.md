# Phase 2 — Real London baseline results

## Executive summary

The first real-data evaluation confirms that a purely lexical category checker is not sufficient for this catalog.

The deterministic baseline achieves moderate precision on the small number of cases it predicts, but recall is very low:

- **Micro precision:** 55.98%
- **Micro recall:** 3.51%
- **Micro F1:** 6.60%
- **Macro precision:** 48.02%
- **Macro recall:** 8.02%
- **Macro F1:** 8.10%

This means the baseline is conservative but misses the overwhelming majority of true category memberships.

The purpose of the baseline was not to maximize accuracy. It was to establish a transparent reference point, expose real failure modes, and determine where semantic reasoning is actually required.

## Dataset acceptance

The source contains:

- 2,341 catalog rows
- 2,341 annotation rows
- 12 human-labelled categories

After requiring a valid name and address identity:

- 2,265 catalog rows have valid identity fields
- 2,264 annotation rows have valid identity fields
- 2,264 valid name+address matches are available for evaluation
- join coverage is **96.71% of all annotations**
- join coverage is **100% of valid annotations**

Rows with invalid identity fields are excluded from semantic evaluation instead of being silently joined on empty keys.

## Baseline coverage

The evaluation set contains:

- 2,264 entities
- 12 category decisions per entity
- 27,168 entity-category evaluation rows
- 4,136 positive human labels

The deterministic baseline predicts only 259 positives.

Of those:

- 145 are true positives
- 114 are false positives
- 3,991 positive human labels are missed

## Category-level findings

### Categories where lexical evidence is especially inadequate

The largest false-negative groups are:

| Category | False negatives |
|---|---:|
| walk | 714 |
| nature | 629 |
| drink | 590 |
| sports | 474 |
| restaurant | 387 |
| nightlife | 353 |
| music | 274 |
| art | 189 |
| dance | 158 |
| history | 112 |
| movie | 81 |

Several categories have effectively zero lexical recall:

- walk: 0%
- drink: 0%
- nightlife: 0%
- movie: 0%

This is expected when category membership is implied by the entity and context rather than stated using the exact category word.

For example, a cinema may clearly belong to the movie category without containing the word "movie", and a park may belong to nature without containing the word "nature".

### Museum behaves differently

Museum has much higher recall:

- precision: 48.69%
- recall: 75.61%
- F1: 59.24%

However, its precision problem is instructive. Many false positives are galleries and exhibition venues that contain lexical cues such as "gallery" or "exhibition" but are not annotated as museums.

This demonstrates a second failure mode: lexical similarity can over-generalize adjacent categories.

## Failure taxonomy discovered from the baseline

The real failures suggest at least three distinct semantic problems:

### 1. Implicit category membership

The entity belongs to a category even when the category term is not present.

Examples:
- parks → nature
- cinemas → movie
- pubs/bars → drink/nightlife
- gyms/raceways → sports

### 2. Adjacent-category confusion

A lexical cue is related to a category but does not imply membership.

Examples:
- gallery ≠ museum
- exhibition venue ≠ museum

### 3. Multi-label context

Many POIs legitimately belong to several categories. A single keyword is insufficient to determine the full label set.

Examples:
- a park may be nature + walk + sports
- a pub may be drink + nightlife + music
- a cultural venue may be art + music + dance

## Decision

The deterministic baseline remains in the system as a cheap and auditable first layer, but it will not be expanded into a large rule library.

Instead, the next phase introduces **atomic semantic evaluators** for category membership.

The first semantic evaluator should answer one narrow question at a time:

> Given the POI name, source metadata and review context, does this entity belong to category X?

This follows the benchmark decision to separate deterministic checks from semantic checks rather than using one general-purpose "find every problem" prompt.

## Why the next phase is semantic rather than more keyword tuning

Additional keyword tuning could improve a few categories, but the failure distribution shows that the dominant issue is not missing synonyms. It is semantic inference.

For example:

- "Hyde Park" implies nature/walk without those words being required.
- "Vue Westfield London" implies movie through entity type.
- "The Prince Albert" may imply drink/nightlife depending on contextual evidence.
- an art gallery containing the word "gallery" should not automatically become a museum.

These require entity understanding and contextual reasoning.

## Next phase

**Phase 3 — Atomic Semantic Category Evaluator**

The next implementation will:

1. define a structured input contract;
2. define one category-membership evaluator schema;
3. use strict JSON output;
4. evaluate one category at a time;
5. version prompt and model configuration;
6. run against the same human-labelled evaluation set;
7. compare deterministic vs semantic precision/recall;
8. inspect disagreements and new failure types;
9. introduce confidence-based routing only after calibration.

The deterministic baseline remains the reference baseline for all future iterations.
