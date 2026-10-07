# Activity Metadata Quality Platform

An eval-driven catalog-quality system for travel marketplace metadata.

## Current implementation phase

The repository now contains a real-data ingestion layer, a deterministic category baseline, and the first atomic semantic category evaluator.

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

## Data policy

Real tourism data is used where a suitable open source exists. Synthetic or controlled enrichment will only be introduced for fields that are absent from the open source and are required to test additional quality dimensions.

## Phase 1 — Real-data foundation

```bash
python -m src.data.run_phase1
```

Outputs:

```text
data/processed/london_profile.json
data/processed/catalog.csv
data/processed/category_evaluation.csv
```

The profile is an acceptance gate: semantic evaluation does not start until join coverage, missingness, duplicates and annotation distribution have been inspected.

## Phase 2 — Deterministic category baseline

```bash
python -m src.evaluation.run_phase2
```

Outputs:

```text
data/processed/category_predictions.csv
data/processed/category_metrics.csv
data/processed/category_failures.csv
data/processed/category_failure_summary.csv
data/processed/phase2_summary.json
```

The real London baseline shows that lexical matching is insufficient: micro precision is about 56% while micro recall is about 3.5%. See `docs/phase-2-real-results.md`.

## Phase 3 — Atomic semantic category evaluator

The first semantic vertical is `museum`. It was selected because the deterministic baseline has both false negatives and adjacent-category false positives such as galleries.

The evaluator processes **one entity × one category** and returns a strict structured decision:

```json
{
  "decision": "member | not_member | uncertain",
  "confidence": 0.0,
  "reason_codes": ["..."],
  "evidence": "..."
}
```

Ground-truth labels and deterministic predictions are never sent to the model. They are merged back only after inference for evaluation.

Run locally after Phase 1 and Phase 2:

```bash
export OPENAI_API_KEY="..."
python -m src.semantic.run_phase3 \
  --category museum \
  --sample-size 240 \
  --model gpt-6-luna
```

Or use the manual **Semantic category calibration** GitHub Actions workflow after adding `OPENAI_API_KEY` as a repository Actions secret.

Phase 3 reports deterministic-vs-semantic precision/recall/F1 on the same calibration set, coverage, abstention rate, token usage and disagreement cases. See `docs/phase-3-semantic-evaluator.md`.

## Testing

```bash
pytest -q
```

The repository keeps raw data and credentials out of source control. Evaluation summaries are committed; full row-level outputs are retained as GitHub Actions artifacts.
