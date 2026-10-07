# Phase 4 — Human adjudication, gold set, and confidence routing

## Executive summary

Phase 3 demonstrated that Gemini materially improves museum-category classification over the deterministic lexical baseline. The remaining errors exposed a second problem: some disagreements are not clearly model failures. They may represent public-label errors, ontology mismatches, or insufficient source evidence.

Phase 4 therefore moves from **model evaluation** to **evaluation-system quality**.

```text
Gemini decision
      ↓
uncertain / label conflict
      ↓
blind-first human review
      ↓
resolution classification
      ↓
adjudicated gold
      ↓
regression cases
      ↓
future prompt / ontology / routing changes
```

No new LLM inference is required to prepare this phase.

## Real review queue

The 240-row museum calibration produces **28 review cases**:

- 14 `UNCERTAIN`
- 6 `HIGH_CONFIDENCE_LABEL_CONFLICT` at Gemini confidence >= 0.90
- 8 other `LABEL_CONFLICT`

Only 11.67% of the calibration sample enters the initial adjudication queue. High-confidence conflicts are reviewed first because they have the highest information value: either the model is confidently wrong, or the label/ontology boundary needs inspection.

## Blind-first review

The Streamlit review UI deliberately hides both the public label and Gemini result during the first judgement.

The reviewer first sees:

- name
- source category
- address
- details
- selected review text

The reviewer records:

- `member`, `not_member`, or `ambiguous`
- reviewer confidence
- evidence / notes

Only after this judgement is locked are the public label and Gemini decision revealed. This reduces anchoring and confirmation bias.

## Resolution taxonomy

Every reviewed case receives one resolution:

- `MODEL_ERROR` — Gemini is wrong under the agreed ontology.
- `PUBLIC_LABEL_ERROR` — the public annotation appears wrong under the agreed ontology.
- `ONTOLOGY_MISMATCH` — the disagreement exposes an unclear or misaligned category definition.
- `INSUFFICIENT_EVIDENCE` — source evidence is not sufficient for a reliable final label.
- `AGREEMENT_AFTER_REVIEW` — the review does not expose a substantive unresolved conflict.

This prevents every disagreement from being incorrectly counted as model failure.

## Gold-set policy

A reviewed `member` or `not_member` case becomes:

```text
label_origin = human_adjudication
gold_status = ADJUDICATED
```

An `ambiguous` case remains:

```text
gold_status = AMBIGUOUS
```

Ambiguous cases remain analyzable but are excluded from regression cases until evidence or ontology improves.

## Confidence routing analysis

The Phase 4 threshold sweep uses the 240-row calibration set only for offline comparison.

| Threshold | Auto coverage | Auto accuracy | Auto errors |
|---:|---:|---:|---:|
| 0.80 | 94.17% | 93.81% | 14 |
| 0.85 | 93.33% | 94.20% | 13 |
| 0.90 | 77.08% | 96.76% | 6 |
| 0.95 | 71.25% | 97.08% | 5 |
| 0.98 | 40.83% | 97.96% | 2 |
| 0.99 | 25.83% | 100.00% | 0 |

A 0.95 threshold illustrates the coverage/accuracy trade-off, but it is **not** a production threshold.

## Why production routing is still disabled

The museum calibration sample is stratified around deterministic failure modes and does not represent natural production prevalence.

Therefore `config/review_routing.yml` explicitly sets:

```text
status = calibration_only
production_enabled = false
```

Production routing requires:

1. adjudication of the unresolved queue;
2. an adjudicated gold/regression set;
3. a representative holdout sample;
4. explicit false-positive and false-negative business costs;
5. threshold validation on the representative holdout.

## Operational workflow

Prepare the queue:

```bash
python -m src.review.run_phase4 \
  --input data/processed/semantic_museum_v1_calibration.csv \
  --category museum
```

Run the review UI:

```bash
pip install -e ".[dev,review]"
streamlit run src/review/app.py
```

Then export gold/regression cases:

```bash
python -m src.review.build_gold \
  --queue data/processed/museum_review_queue.csv \
  --adjudications data/processed/museum_adjudications.csv \
  --gold data/processed/museum_adjudicated_gold.csv \
  --regression data/processed/museum_regression_cases.csv
```

## Decision gate for Phase 5

Before expanding to more categories or automated remediation, answer:

1. How many apparent semantic errors are true model errors?
2. How many are public-label errors?
3. Which ontology boundaries need rewriting?
4. Which high-confidence mistakes belong in regression tests?
5. What auto-routing threshold is justified on a representative holdout?
