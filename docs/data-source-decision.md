# Data Source Decision: London Tourism POIs

## Decision

Use the **Enriched Tourism Dataset London (POIs)** as the first real-world source for the catalog-quality prototype.

The project uses two files:

- `London.csv`: enriched tourism POI metadata.
- `London_annotated.csv`: human-created ground-truth category annotations.

## Why this source

The first release requires both realistic tourism metadata and an evaluation reference set. The London dataset provides real POI names, categories, addresses, coordinates, details and reviews, while the annotated file provides human category labels.

This allows the category-quality evaluation pipeline to start with real-world data rather than fully synthetic records.

## Limitations

The dataset represents tourism POIs rather than bookable activity inventory. It does not provide all marketplace-specific fields required by the broader quality system, such as activity options, pickup configuration, private/shared status or guide type.

Those fields will not be fabricated into the base source. They will be introduced later through a clearly separated enrichment layer only for quality dimensions that cannot be evaluated from the source data itself.

## Source and license

- Dataset: Enriched Tourism Dataset London (POIs)
- DOI: `10.6084/m9.figshare.27628029`
- License: CC BY 4.0
- Authors: Ramon Hermoso, Sergio Ilarri, Raquel Trillo-Lado

Any redistributed or derived artifacts must preserve attribution required by the license.
