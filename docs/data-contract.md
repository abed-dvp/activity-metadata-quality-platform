# Data Contract: London POI Source

## Purpose

The London source is the first real-world catalog input to the quality platform. The raw source is preserved unchanged; downstream code maps it into a stable canonical schema before any quality logic is applied.

## Canonical catalog fields

| Field | Meaning | Requirement |
|---|---|---|
| `entity_id` | Stable project-level identifier | required |
| `source_id` | Identifier from the source dataset | required |
| `name` | POI name | required |
| `source_category` | Original source category when present | optional |
| `address` | Source address/location text | required |
| `latitude` | WGS84 latitude | optional but validated when present |
| `longitude` | WGS84 longitude | optional but validated when present |
| `details` | Source descriptive metadata | optional |
| `review_text` | Source review-derived text | optional |
| `dataset_name` | Data provenance | required |
| `dataset_version` | Versioned provenance marker | required |
| `license` | Redistribution/use license | required |

## Ground truth

`London_annotated.csv` contains human-created multi-label category annotations. The pipeline keeps the raw annotation matrix and also converts it into a long-form evaluation table with one row per `(entity, category)` pair.

The annotation source is not modified or treated as model output. It is the external reference used to evaluate category-quality checks.

## Join policy

The published files do not expose a documented shared numeric identifier between the canonical metadata file and the annotation file. The first implementation therefore joins on normalized `name + address`, and the pipeline must report join coverage before model evaluation is accepted.

If inspection of the downloaded source reveals a stronger stable key, the join policy should be upgraded and captured as an architecture decision.

## Validation policy

Deterministic validation is performed before semantic evaluation. Initial checks include:

- required fields
- duplicate entity IDs
- latitude range
- longitude range

Further source-specific checks are added only after actual raw-file profiling confirms the field distributions.
