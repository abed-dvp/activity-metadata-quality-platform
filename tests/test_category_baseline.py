import pandas as pd

from src.baselines.category_keyword import BaselineConfig, predict_categories
from src.evaluation.category_report import evaluate_predictions
from src.evaluation.failure_analysis import extract_failures, summarize_failures


def test_keyword_baseline_uses_text_without_ground_truth_leakage():
    df = pd.DataFrame(
        {
            "entity_id": ["a", "b", "c"],
            "name": ["British Museum", "Hyde Park", "River Cruise"],
            "source_category": ["attraction", "attraction", "attraction"],
            "details": ["Historic collections", "Large public garden", "Boat sightseeing"],
            "review_text": ["Great exhibitions", "Beautiful green space", "Nice views"],
            "category": ["museum", "park", "museum"],
            "is_member": [1, 1, 0],
        }
    )
    config = BaselineConfig(
        aliases={
            "museum": ("museum", "exhibition", "collection"),
            "park": ("park", "garden", "green space"),
        },
        threshold=2.0,
    )

    out = predict_categories(df, config)
    assert list(out["prediction"]) == [1, 1, 0]
    assert out.loc[0, "baseline_score"] >= 2.0
    assert "name:museum" in out.loc[0, "prediction_evidence"]


def test_failure_analysis_separates_false_positive_and_false_negative():
    predictions = pd.DataFrame(
        {
            "entity_id": ["a", "b", "c"],
            "name": ["A", "B", "C"],
            "category": ["museum", "museum", "park"],
            "is_member": [1, 0, 1],
            "prediction": [0, 1, 1],
            "baseline_score": [0.0, 3.0, 3.0],
            "prediction_evidence": ["", "name:museum", "name:park"],
        }
    )
    failures = extract_failures(predictions)
    assert set(failures["error_type"]) == {"FALSE_POSITIVE", "FALSE_NEGATIVE"}
    summary = summarize_failures(failures)
    assert int(summary["count"].sum()) == 2


def test_category_report_includes_macro_and_micro_summaries():
    predictions = pd.DataFrame(
        {
            "entity_id": ["a", "b", "a", "b"],
            "category": ["museum", "museum", "park", "park"],
            "is_member": [1, 0, 0, 1],
            "prediction": [1, 1, 0, 1],
        }
    )
    report = evaluate_predictions(predictions)
    assert "__micro_overall__" in set(report["category"])
    assert "__macro_average__" in set(report["category"])
    museum = report.loc[report["category"] == "museum"].iloc[0]
    assert museum["positives"] == 1
    assert museum["predicted_positives"] == 2
    assert museum["precision"] == 0.5


def test_failure_analysis_handles_perfect_predictions():
    predictions = pd.DataFrame(
        {
            "entity_id": ["a", "b"],
            "category": ["museum", "park"],
            "is_member": [1, 0],
            "prediction": [1, 0],
        }
    )
    failures = extract_failures(predictions)
    assert failures.empty
    assert "error_type" in failures.columns
