# Quality Action Policy

## Executive summary

The Unified Quality Impact Score now feeds a policy layer that answers:

> What should happen next for this listing?

The policy deliberately separates **internal automation** from **external action**.

Allowed automatically:

- prioritize an internal review queue;
- attach a reason and likely remediation lane;
- request more evidence internally.

Not allowed automatically:

- contact a supplier;
- overwrite coordinates;
- change category assignments;
- publish metadata corrections.

## Decision logic

```text
Unified Quality Impact Score
          +
Coverage / evidence state
          ↓
      Action Policy
          ↓
┌───────────────────────────────┐
│ PASS                          │
│ NEED_MORE_EVIDENCE            │
│ HUMAN_REVIEW                  │
└───────────────────────────────┘
          ↓
only after human confirmation
          ↓
┌───────────────────────────────┐
│ supplier fix request candidate│
│ coordinate fix candidate      │
│ category fix candidate        │
└───────────────────────────────┘
```

## Coverage guard

A `partial` score can never produce `PASS`.

Even a partial score of zero means only:

> no issue observed in the domain we evaluated.

It does **not** mean the full listing is clean.

## Field-specific lanes

### Supplier content

When a fully evaluated listing has evidence that the address itself is deficient:

```text
ADDRESS_QUALITY_REVIEW
    → HUMAN_REVIEW
    → if independently confirmed
    → SUPPLIER_FIX_REQUEST_CANDIDATE
```

Supplier contact remains disabled.

### Location evidence

Ambiguous geocoding, entity mismatch, and boundary cases stay in internal review.

### Coordinate mismatch

A coordinate can only become an internal coordinate-fix candidate after human confirmation.

### Category

Category evidence routes to taxonomy/content operations rather than being silently reclassified.

## Internal auto-flag

A MEDIUM or HIGH fully evaluated issue may be automatically **flagged inside the review system**.

This is a queue-prioritization action, not a supplier-facing or catalog-mutating action.

## Production status

`production_enabled = false`

The policy is an auditable prototype for demonstrating how evaluation outputs can drive operational workflows safely.
