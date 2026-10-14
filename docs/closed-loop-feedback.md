# Closed-loop feedback and remediation evaluation

## Objective

The platform now closes the loop between:

```text
quality evaluation
      ↓
action queue
      ↓
review / adjudication
      ↓
structured feedback
      ↓
learning event
      ↓
regression safety set
      ↓
future evaluator / routing validation
```

The goal is **not** automatic self-training.

The goal is to make every reviewed case reusable evidence.

## Feedback trust tiers

### Assisted evidence review

Evidence-supported adjudication performed with AI assistance.

Allowed:

- produce a structured learning event;
- create a regression safety case;
- verify that a known false-positive pattern does not return.

Not allowed:

- count as independent human gold;
- calibrate confidence thresholds;
- trigger retraining;
- justify production automation.

### Independent human gold

A future independent reviewer decision can be marked as human-gold eligible.

Only this tier may become threshold-calibration evidence.

## Initial feedback

The current loop contains two assisted Location cases:

- Acorn 20/20 — address context incomplete;
- The Corrib Rest — street-name typo.

Both cases confirmed an address-side defect and did **not** support changing the coordinate.

Therefore their regression requirement is:

```text
expected route  = ADDRESS_OR_GEOCODER_REVIEW
forbidden route = COORDINATE_MISMATCH_CANDIDATE
```

This protects the address-first safety behavior learned earlier in the project.

## Remediation candidates

The feedback table may store a proposed remediation, but the pipeline does not apply it.

Examples:

- enrich an incomplete address;
- correct a street-name typo.

A later workflow could re-evaluate corrected metadata in a sandbox before any catalog mutation.

## Governance

Feedback ingestion alone:

- does not retrain Gemini;
- does not change thresholds;
- does not change supplier metadata;
- does not contact suppliers;
- does not enable production routing.

The loop is therefore **evaluation-driven learning**, not uncontrolled online learning.
