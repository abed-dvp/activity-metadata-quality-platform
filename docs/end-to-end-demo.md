# End-to-end demo

## Interview objective

This is the shortest path through the project for a product/AI interview.

Instead of walking through every implementation phase, run one real listing through the complete decision system:

```text
listing
  ↓
detect inconsistency
  ↓
quality gate
  ↓
impact score
  ↓
action policy
  ↓
review feedback
  ↓
regression safety case
```

## Run

No API key is required.

```bash
python -m src.demo.run_demo
```

The default case is **Acorn 20/20** because it demonstrates the most important safety behavior in the project.

## The story

The source listing contains:

```text
Acorn 20/20
20 Richmond Rd
51.41304021, -0.300514441
```

A naive geocoding comparison returns a reference about **26.9 km away**.

The platform does **not** conclude:

```text
bad pin → overwrite coordinate
```

Instead:

```text
26.9 km disagreement
      ↓
entity/address quality gate
      ↓
ADDRESS_OR_GEOCODER_REVIEW
      ↓
Quality Impact Score = 35
      ↓
HUMAN_REVIEW
      ↓
assisted evidence review
      ↓
confirmed: address context incomplete
      ↓
coordinate remains unchanged
      ↓
regression case created
```

The review found that the venue is at **20 Richmond Road, Kingston upon Thames, KT2 5BE**. The original address omitted the locality/postcode, so the geocoder resolved a different Richmond Road.

## Product message

The important product behavior is not merely anomaly detection.

It is **diagnosis + safe action selection**.

The system distinguishes:

- evidence that two fields disagree;
- evidence about which field is likely wrong;
- confidence/coverage;
- whether a human must review;
- whether an external action is permitted.

## Governance demonstrated

The demo also shows:

- no automatic supplier contact;
- no automatic metadata mutation;
- no automatic coordinate overwrite;
- assisted review is not human gold;
- feedback can create regression protection without silently changing thresholds.

## Output

The workflow commits:

- `reports/demo/end_to_end_demo.json`
- `reports/demo/end_to_end_demo.md`

These are presentation-ready snapshots generated entirely from cached evaluation artifacts.
