# Location Quality — deterministic real-data baseline

## Objective

Validate whether the London POI catalog contains usable, geographically plausible location metadata before introducing semantic or externally enriched location checks.

This stage intentionally starts with deterministic checks because they are auditable, cheap, and sufficient to expose basic catalog defects.

## Checks

The first baseline evaluates:

- missing coordinate pairs;
- partial latitude/longitude pairs;
- invalid WGS84 latitude/longitude ranges;
- near-`0,0` null-island sentinel coordinates;
- coordinates outside a deliberately broad London plausibility envelope.

The London envelope is a **source-specific diagnostic**, not a production geofence. A valid travel marketplace can contain activities outside a city, meeting points, pickup locations, or multi-location products.

## What this baseline does not claim

It does **not** yet prove that:

- the textual address matches the coordinate;
- the coordinate is the correct entrance or meeting point;
- the supplier-selected city/region is semantically correct;
- pickup and meeting-point metadata are consistent.

Those questions require stronger reference evidence than the current open dataset provides.

## Run

```bash
python -m src.data.run_phase1
python -m src.evaluation.run_location_baseline
```

Outputs:

- `data/processed/location_findings.csv`
- `data/processed/location_summary.json`

## Decision gate

If the real-data baseline shows only basic completeness/range defects, the next step is to add an evidence-backed address-coordinate consistency check.

If the open dataset lacks enough reference information for that check, use controlled augmentation rather than fabricating labels.

Production routing remains disabled.
