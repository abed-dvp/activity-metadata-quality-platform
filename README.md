# Activity Metadata Quality Platform

An eval-driven catalog-quality system for travel marketplace metadata.

## Current implementation phase

The repository currently establishes the first real-world data source and the category ground-truth ingestion path.

### Data source

The first source is the **Enriched Tourism Dataset London (POIs)**, an open tourism dataset with a human-annotated category ground truth.

- DOI: `10.6084/m9.figshare.27628029`
- License: CC BY 4.0

The raw files are downloaded at runtime and are intentionally not committed to the repository.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e .[dev]
```

Download the public London dataset:

```bash
python -m src.data.download_london
```

Inspect the raw files:

```bash
python -m src.data.inspect_london
```

Convert the human annotations into a normalized category ground-truth table:

```bash
python -m src.data.prepare_category_ground_truth
```

## Data policy

Real tourism data is used where a suitable open source exists. Synthetic or controlled enrichment will only be introduced for fields that are absent from the open source and are required to test additional quality dimensions.

## Phase 1: profile and normalize the real source

Once the two official CSV files are available under `data/raw/`, run the complete Phase 1 pipeline:

```bash
python -m src.data.run_phase1
```

This produces:

```text
data/processed/london_profile.json
data/processed/catalog.csv
data/processed/category_evaluation.csv
```

`london_profile.json` is an acceptance gate: semantic evaluation should not begin until join coverage, duplicate rates, missingness and annotation distribution have been inspected.

If automated download is blocked by the hosting environment, download the two files from the official dataset page and place them at:

```text
data/raw/London.csv
data/raw/London_annotated.csv
```

The pipeline itself is independent of the download mechanism.

## Phase 2: deterministic category baseline

After Phase 1 has produced `data/processed/category_evaluation.csv`, run:

```bash
python -m src.evaluation.run_phase2
```

The first category evaluator is intentionally deterministic and interpretable. It establishes a measurable baseline before semantic/LLM evaluation is introduced.

Outputs:

```text
data/processed/category_predictions.csv
data/processed/category_metrics.csv
data/processed/category_failures.csv
data/processed/category_failure_summary.csv
data/processed/phase2_summary.json
```

The main review artifact is the failure set: false positives and false negatives are used to define the next atomic semantic evaluators. See `docs/phase-2-category-baseline.md`.
