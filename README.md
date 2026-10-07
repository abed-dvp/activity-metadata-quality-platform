# Activity Metadata Quality Platform

An eval-driven catalog-quality system for travel marketplace metadata.

The repository implements a real-data pipeline, deterministic quality checks, an atomic Gemini semantic evaluator, and a human adjudication loop for building stronger gold/regression datasets.

## Data source

The first source is the **Enriched Tourism Dataset London (POIs)** with human category annotations.

- DOI: `10.6084/m9.figshare.27628029`
- License: CC BY 4.0

Raw external files are downloaded at runtime and are not committed.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e .[dev]
```

For the human-review UI:

```bash
pip install -e ".[dev,review]"
```

## Phase 1 — Real-data foundation

```bash
python -m src.data.download_london
python -m src.data.run_phase1
```

## Phase 2 — Deterministic category baseline

```bash
python -m src.evaluation.run_phase2
```

The baseline is an auditable lexical reference and exposes false-positive / false-negative failure modes.

## Phase 3 — Atomic Gemini semantic evaluator

The first semantic vertical is `museum`: one entity × one target category × one structured decision.

```json
{
  "decision": "member | not_member | uncertain",
  "confidence": 0.0,
  "reason_codes": ["..."],
  "evidence": "..."
}
```

The provider uses the official Google GenAI SDK with Gemini `generateContent`, JSON Schema structured output, and low thinking for calibration.

```bash
export GEMINI_API_KEY="..."
python -m src.semantic.run_phase3 \
  --category museum \
  --sample-size 240 \
  --model gemini-3.8-flash
```

The 240-row failure-aware calibration reached about 92% precision/recall/F1 on decided cases. This is calibration evidence, not production validation. See `docs/phase-3-real-results.md`.

## Phase 4 — Human adjudication and confidence routing

Phase 4 converts semantic uncertainty and label conflicts into a review queue, records blind-first human judgements, builds an adjudicated gold set, and exports regression cases.

Prepare the queue:

```bash
python -m src.review.run_phase4 \
  --input data/processed/semantic_museum_v1_calibration.csv \
  --category museum
```

Run the review UI:

```bash
export REVIEW_INPUT="data/processed/semantic_museum_v1_calibration.csv"
export ADJUDICATION_OUTPUT="data/processed/museum_adjudications.csv"
export REVIEWER_ID="reviewer-name"
streamlit run src/review/app.py
```

The UI is blind-first: the reviewer judges the entity before the public label and Gemini decision are revealed.

After review:

```bash
python -m src.review.build_gold \
  --queue data/processed/museum_review_queue.csv \
  --adjudications data/processed/museum_adjudications.csv \
  --gold data/processed/museum_adjudicated_gold.csv \
  --regression data/processed/museum_regression_cases.csv
```

Routing thresholds in Phase 4 are explicitly **calibration-only**. They are not production thresholds until adjudication and representative holdout validation are complete. See `docs/phase-4-human-adjudication.md`.

## Testing

```bash
pytest -q
```

Raw data, credentials, row-level semantic outputs, and reviewer work products remain outside source control by default. Compact evaluation summaries and design decisions are committed for auditability.


## Phase 5 — Representative holdout

Phase 5 excludes the full Phase 3 calibration set and validates the frozen museum evaluator on residual data.

The representative 600-row holdout achieved 95.3% model coverage. A conservative confidence threshold of 0.98 produced 60.2% auto-route coverage with zero errors against the public-label reference in that sample. Production routing remains disabled because Phase 4 identified probable annotation/ontology mismatches.

See `docs/phase-5-real-results.md`.
