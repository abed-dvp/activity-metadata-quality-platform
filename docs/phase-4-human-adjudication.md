# Phase 4 — Human adjudication, gold set, and confidence routing

## Executive summary

Phase 3 demonstrated that Gemini materially improves museum-category classification over the deterministic lexical baseline. The remaining errors exposed a second problem: some disagreements are not clearly model failures. They may represent public-label errors, ontology mismatches, or insufficient source evidence.

Phase 4 therefore moves from **model evaluation** to **evaluation-system quality**.

```text
Gemini decision
      ↓
uncertain / label conflict
      ↓
blind-first review
      ↓
resolution classification
      ↓
adjudicated or candidate gold
      ↓
regression cases only after final human review
```

No new LLM inference is required to prepare this phase.

## Real review queue

The 240-row museum calibration produces **28 review cases**:

- 14 `UNCERTAIN`
- 6 `HIGH_CONFIDENCE_LABEL_CONFLICT` at Gemini confidence >= 0.90
- 8 other `LABEL_CONFLICT`

Only 11.67% of the calibration sample enters the initial adjudication queue. High-confidence conflicts are reviewed first because they have the highest information value: either the model is confidently wrong, or the label/ontology boundary needs inspection.

## Blind-first human review

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

## Gold governance

The system distinguishes review provenance.

A final human judgement:

```text
reviewer_type = human
review_status = FINAL_HUMAN_REVIEW
```

can become:

```text
label_origin = human_adjudication
gold_status = ADJUDICATED
```

and is eligible for regression.

An assistant first pass:

```text
reviewer_type = assistant_first_pass
review_status = PROVISIONAL_ASSISTED_REVIEW
```

can only become:

```text
label_origin = assisted_adjudication_candidate
gold_status = CANDIDATE_NOT_HUMAN_FINAL
```

and is **not** eligible for regression until a human reviewer finalizes it.

Ambiguous cases remain analyzable but stay out of regression.

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

Production routing requires:

1. final human adjudication of unresolved cases;
2. a human-adjudicated gold/regression set;
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

See `docs/phase-4-assisted-adjudication-results.md` for the first provisional review pass.
