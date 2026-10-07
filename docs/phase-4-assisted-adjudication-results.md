# Phase 4.1 — Provisional assisted adjudication results

## Status

This is an **assistant first-pass review**, not final human adjudication.

The purpose is to reduce the 28-case review queue into:

- cases with enough evidence to become **candidate gold**;
- cases that remain genuinely ambiguous and need a human reviewer or additional evidence.

No provisional case is promoted into the regression set.

## Results

All 28 queued museum cases were reviewed against the project ontology and the evidence already present in the London dataset.

### Reviewer outcomes

- 17 resolved candidate labels
- 11 ambiguous / insufficient-evidence cases

Candidate-label distribution:

- 7 `member`
- 10 `not_member`

Resolution taxonomy:

- 13 `PUBLIC_LABEL_ERROR`
- 11 `INSUFFICIENT_EVIDENCE`
- 3 `ONTOLOGY_MISMATCH`
- 1 `AGREEMENT_AFTER_REVIEW`
- 0 clear `MODEL_ERROR` in this provisional pass

This does **not** prove that Gemini made no errors. The queue is intentionally enriched for label conflicts, and the first-pass review uses the same explicit project ontology that the semantic evaluator was instructed to follow.

## Important ontology cases

Three cases should not be treated as simple label corrections:

### Science Museum IMAX

The entity is a cinema amenity inside a museum. The open question is whether a child/sub-venue should inherit the parent's museum category.

### Somerset House

The venue is a mixed-use historic/cultural site with exhibitions and events. The boundary between museum, cultural venue, and historic attraction needs explicit product policy.

### National Maritime Museum Gardens

The entity name points to the gardens while the review evidence appears to describe the parent museum. This is a parent/adjacent-entity identity issue as much as a category issue.

These cases should feed an ontology rule for **entity scope and inheritance**, not only model prompting.

## Ambiguous cases

Eleven cases remain unresolved because the source evidence does not establish whether the venue is a public interpretive institution or a commercial/generic gallery space.

Examples include:

- Strand Gallery
- Contemporary Ceramics Centre
- Zebra Gallery
- Annroy Gallery
- London Sewing Machine Museum
- Decima Gallery
- Gallery One and a Half
- Gallery Vela
- Hepsibah Gallery
- Pond Gallery
- http Gallery

These should not enter regression until a human reviewer or additional trusted evidence resolves them.

## Candidate gold vs existing signals

Among the 17 resolved candidate cases:

- Gemini agrees with the candidate label on 14 cases.
- The public label agrees with the candidate label on 1 case.
- The remaining 3 are cases where Gemini abstained and the assisted review selected a provisional label.

This comparison is **not a production accuracy metric**. It only describes the conflict-heavy review queue.

## Governance decision

The project now distinguishes two review states:

```text
assistant_first_pass
+ PROVISIONAL_ASSISTED_REVIEW
→ candidate gold only
→ never enters regression automatically
```

and:

```text
human
+ FINAL_HUMAN_REVIEW
→ adjudicated gold
→ eligible for regression cases
```

This prevents AI-assisted review from being mislabeled as human ground truth.

## Next step

The next high-value action is one of:

1. human sign-off on the 17 candidate cases; and
2. evidence enrichment / human review for the 11 ambiguous cases.

Only final human decisions should be promoted into the regression set and used to validate production routing thresholds.
