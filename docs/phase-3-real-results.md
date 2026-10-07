# Phase 3 — Real Gemini museum calibration results

## Executive summary

The first real semantic category calibration shows a large improvement over the deterministic lexical baseline on the same 240-row, failure-aware calibration sample.

The semantic evaluator uses:

- model: `gemini-3.8-flash`
- provider path: Google Gemini `generateContent`
- prompt: `category_membership_v1`
- thinking level: `low`
- target category: `museum`
- sample size: 240

The sample is deliberately stratified around deterministic true positives, false positives, false negatives, and true negatives. It is designed for evaluator calibration and failure analysis; it is **not** a production-prevalence estimate.

## Headline results

| Metric | Deterministic baseline | Gemini decided cases |
|---|---:|---:|
| Precision | 50.82% | 91.95% |
| Recall | 67.39% | 91.95% |
| F1 | 57.94% | 91.95% |

Gemini abstained on 14 of 240 cases:

- coverage: **94.17%**
- abstention rate: **5.83%**

When `uncertain` is treated conservatively as no automatic positive action:

- precision: **91.95%**
- recall: **86.96%**
- F1: **89.39%**

## Confusion counts

### Deterministic baseline

- true positives: 62
- false positives: 60
- false negatives: 30
- true negatives: 88

### Gemini — decided cases only

- true positives: 80
- false positives: 7
- false negatives: 7
- true negatives: 132

### Gemini — conservative routing

With uncertain cases routed away from automatic positive action:

- true positives: 80
- false positives: 7
- false negatives: 12
- true negatives: 141

This is the more operationally relevant view for a human-in-the-loop system.

## What improved

### 1. Adjacent-category false positives fell sharply

The lexical baseline often promoted galleries and exhibition spaces into `museum` because of terms such as `gallery`, `exhibition`, or related art vocabulary.

The semantic evaluator can reason about the ontology boundary between:

- an institutional museum / interpretive visitor venue;
- a commercial gallery;
- a temporary exhibition/event space;
- a venue adjacent to a museum experience.

This reduced false positives from **60 to 7** on the calibration sample.

### 2. Implicit membership was recovered

The baseline misses entities where museum membership is implied by entity type and context rather than an exact keyword.

Gemini recovered many of those cases, reducing false negatives from **30 to 7** among decided rows.

### 3. Abstention behaved usefully

Fourteen cases were returned as `uncertain` rather than forced into a binary answer.

Typical uncertain cases had insufficient evidence to distinguish:

- institutional gallery vs commercial gallery;
- museum venue vs adjacent garden/amenity;
- visitor-facing collection vs organization/project;
- genuine museum vs commercial shop using museum-like language.

This is the behavior required for later human-review routing.

## Important disagreement examples

Some of the remaining errors are likely not simple model failures. They expose possible ontology-vs-dataset-label disagreements.

### Human label says not museum, evaluator says museum

Examples include:

- Old Operating Theatre Museum & Herb Garret
- Kew Bridge Steam Museum
- Guildhall Art Gallery
- Serpentine Gallery

For the first two, the entity name and review evidence strongly resemble the project ontology's museum definition. These cases should be reviewed as potential **ground-truth / ontology mismatch**, not blindly counted as prompt failure.

### Human label says museum, evaluator says not museum

Examples include:

- White Cube
- Maureen Paley
- The Rag Factory
- Somerset House
- Guildhall

Several of these are galleries, event/exhibition venues, or historic buildings. The evaluator is applying the explicit project exclusion boundary more strictly than the public annotation set appears to.

### High-value ambiguous examples

Useful abstention cases include:

- Contemporary Ceramics Centre
- National Maritime Museum Gardens
- London Sewing Machine Museum
- The Portable Antiquities Scheme
- several small galleries with insufficient commercial/institutional context

These should become human-review / ontology-calibration cases.

## Cost

The full 240-row run used:

- input tokens: **134,034**
- output + thinking tokens: **24,517**

At the October 2026 standard Gemini 3.8 Flash introductory prices of:

- $0.75 / 1M input tokens
- $3.75 / 1M output tokens

the successful full calibration inference is approximately **$0.19**.

The preceding successful 60-row smoke run used 34,652 input tokens and 6,796 output/thinking tokens, approximately **$0.05**.

Successful inference spend for the smoke + full calibration is therefore approximately **$0.24**, well below the project's €5 execution ceiling. Actual cloud billing remains authoritative.

## Decision

The semantic evaluator has demonstrated enough value to remain in the architecture.

However, the current result is **calibration evidence, not production validation**.

The next phase should not immediately expand prompts across every category. First:

1. manually review the high-confidence semantic errors;
2. distinguish true model errors from ontology/ground-truth mismatches;
3. convert reviewed cases into a small adjudicated gold set;
4. define confidence/risk routing thresholds;
5. validate on a representative holdout sample rather than the stratified calibration set.

Only after that gate should the same atomic evaluator framework be expanded to categories such as nature, walk, drink, or nightlife.

## Artifacts

The GitHub Actions calibration artifact contains:

- `semantic_museum_v1_calibration.csv`
- `semantic_museum_v1_disagreements.csv`
- `semantic_museum_v1_summary.json`

The row-level outputs are kept as Actions artifacts rather than committed to the repository.
