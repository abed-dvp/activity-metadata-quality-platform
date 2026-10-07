import pandas as pd

from src.data.london_schema import resolve_mapping
from src.data.prepare_london_catalog import prepare_catalog
from src.data.build_evaluation_dataset import build_evaluation_dataset
from src.quality.deterministic import validate_catalog
from src.evaluation.metrics import binary_metrics


def sample_raw_catalog():
    return pd.DataFrame(
        {
            "id": [1, 2],
            "name": ["British Museum", "Hyde Park"],
            "category": ["attraction", "attraction"],
            "address": ["Great Russell Street", "London"],
            "latitude": [51.5194, 51.5073],
            "longitude": [-0.1270, -0.1657],
            "details": ["Museum and collections", "Large public park"],
            "review_text": ["Excellent museum", "Beautiful green space"],
        }
    )


def test_schema_mapping_and_catalog_preparation():
    raw = sample_raw_catalog()
    mapping = resolve_mapping(raw)
    assert mapping["source_id"] == "id"
    assert mapping["name"] == "name"

    catalog = prepare_catalog(raw)
    assert list(catalog["entity_id"]) == ["london_poi_1", "london_poi_2"]
    assert catalog["latitude"].dtype.kind == "f"


def test_category_evaluation_join():
    catalog = prepare_catalog(sample_raw_catalog())
    annotated = pd.DataFrame(
        {
            "POI Name": ["British Museum", "Hyde Park"],
            "Address": ["Great Russell Street", "London"],
            "Museum": [1, None],
            "Park": [None, 1],
        }
    )
    evaluation = build_evaluation_dataset(catalog, annotated)
    assert len(evaluation) == 4
    assert evaluation["is_member"].sum() == 2
    assert set(evaluation["category"]) == {"museum", "park"}


def test_deterministic_quality_checks():
    catalog = prepare_catalog(sample_raw_catalog())
    catalog.loc[0, "latitude"] = 200
    findings = validate_catalog(catalog)
    assert "INVALID_LATITUDE" in set(findings["defect_type"])


def test_binary_metrics():
    result = binary_metrics([1, 1, 0, 0], [1, 0, 1, 0])
    assert result.true_positive == 1
    assert result.false_positive == 1
    assert result.false_negative == 1
    assert result.true_negative == 1
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.f1 == 0.5

from src.data.profile_london import profile_dataset
from src.evaluation.category_report import evaluate_predictions


def test_profile_dataset_reports_join_coverage_and_categories():
    raw = sample_raw_catalog()
    annotated = pd.DataFrame(
        {
            "POI Name": ["British Museum", "Hyde Park"],
            "Address": ["Great Russell Street", "London"],
            "Museum": [1, None],
            "Park": [None, 1],
        }
    )
    profile = profile_dataset(raw, annotated)
    assert profile["catalog_rows"] == 2
    assert profile["annotation_rows"] == 2
    assert profile["annotation_category_count"] == 2
    assert profile["join_coverage_vs_annotations"] == 1.0
    assert profile["positive_labels_by_category"]["museum"] == 1


def test_category_report_is_per_category_and_overall():
    predictions = pd.DataFrame(
        {
            "entity_id": ["a", "b", "a", "b"],
            "category": ["museum", "museum", "park", "park"],
            "is_member": [1, 0, 0, 1],
            "prediction": [1, 1, 0, 1],
        }
    )
    report = evaluate_predictions(predictions)
    assert set(report["category"]) == {"museum", "park", "__micro_overall__", "__macro_average__"}
    museum = report.loc[report["category"] == "museum"].iloc[0]
    assert museum["precision"] == 0.5
    assert museum["recall"] == 1.0
