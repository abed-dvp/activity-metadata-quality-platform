# End-to-end executive demo

## 60-second story

The platform detected a large location inconsistency, used quality gates to avoid a false bad-pin conclusion, routed the case to review, captured the confirmed address defect, and converted the outcome into a regression safety case without changing supplier metadata automatically.

## Listing

- **Acorn 20/20**
- Source address: `20 Richmond Rd`
- Source coordinates: `51.41304021, -0.300514441`

## 1. Detect

- Address ↔ coordinate disagreement: **26915.4 m**
- Raw diagnostic: `suspicious`

## 2. Quality gate

- Route: `ADDRESS_OR_GEOCODER_REVIEW`
- Likely bad field: `address_or_reference_match`
- Automatic coordinate overwrite: **False**

## 3. Quality Impact Score

- Score: **35/100**
- Priority: **MEDIUM**
- Coverage: **partial (0.5)**

## 4. Action policy

- Action: `HUMAN_REVIEW`
- Lane: `EVIDENCE_GAP`
- Internal auto-flag: **True**
- Supplier contact: **False**
- Metadata mutation: **False**

## 5. Review feedback

- Confirmed bad field: **address**
- Root cause: **ADDRESS_CONTEXT_INCOMPLETE**
- Remediation candidate: `20 Richmond Road, Kingston upon Thames, KT2 5BE`
- Human gold eligible: **False**

## 6. Closed-loop regression

- Expected safe route: `ADDRESS_OR_GEOCODER_REVIEW`
- Forbidden regression: `COORDINATE_MISMATCH_CANDIDATE`
- Allowed for threshold calibration: **False**

## Why this matters

A naive pipeline would have treated a 26.9 km geocoder disagreement as a bad pin. This pipeline separates detection from diagnosis, keeps external side effects disabled, and turns reviewed mistakes into reusable regression evidence.
