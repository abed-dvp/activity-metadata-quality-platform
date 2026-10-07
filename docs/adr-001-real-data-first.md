# ADR-001: Use real open tourism data as the initial catalog source

**Status:** Accepted

## Context

The system needs realistic tourism entities and independently created labels in order to measure quality rather than only demonstrate generated examples.

## Decision

Use the Enriched Tourism Dataset London (POIs) as the first source. Preserve raw data unchanged, map it into a canonical schema, and use the separately published human annotations as category ground truth.

Synthetic enrichment is deferred to quality dimensions that are absent from the public source, such as pickup, guide type, private/shared options, and activity-level logistics.

## Rationale

This sequencing separates two questions that should not be conflated:

1. Can the evaluation system measure category quality on real tourism entities?
2. How should missing marketplace-specific dimensions be simulated or enriched later?

Starting with real data reduces uncertainty in the first question. Controlled enrichment can then be introduced with explicit provenance when additional domains are implemented.

## Consequences

- Category quality can be evaluated against external human labels from the first release.
- Location validation can begin on real addresses and coordinates.
- Marketplace-specific attribute consistency remains out of the initial data milestone.
- A canonical schema is required so that the source can later be replaced or supplemented by the German Tourism Knowledge Graph without rewriting downstream quality logic.
