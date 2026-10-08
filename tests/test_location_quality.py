import pandas as pd

from src.quality.location import summarize_location_quality, validate_location_quality


def test_location_quality_flags_missing_partial_invalid_and_outside_bounds():
    catalog = pd.DataFrame(
        {
            "entity_id": ["ok", "missing", "partial", "invalid", "null-island", "outside"],
            "latitude": [51.50, None, 51.50, 95.0, 0.0, 48.85],
            "longitude": [-0.12, None, None, -0.12, 0.0, 2.35],
        }
    )

    findings = validate_location_quality(catalog)
    defects = set(findings["defect_type"])

    assert "MISSING_COORDINATES" in defects
    assert "PARTIAL_COORDINATE_PAIR" in defects
    assert "INVALID_LATITUDE" in defects
    assert "NULL_ISLAND_COORDINATES" in defects
    assert "OUTSIDE_LONDON_PLAUSIBILITY_BOUNDS" in defects
    assert "ok" not in set(findings["entity_id"])


def test_location_summary_reports_entity_rate_not_only_issue_count():
    catalog = pd.DataFrame(
        {
            "entity_id": ["ok", "bad"],
            "latitude": [51.50, None],
            "longitude": [-0.12, None],
        }
    )
    findings = validate_location_quality(catalog)
    summary = summarize_location_quality(catalog, findings)

    assert summary["catalog_rows"] == 2
    assert summary["complete_coordinate_pairs"] == 1
    assert summary["coordinate_pair_coverage"] == 0.5
    assert summary["entities_with_location_findings"] == 1
    assert summary["entity_finding_rate"] == 0.5
    assert summary["production_routing_enabled"] is False
