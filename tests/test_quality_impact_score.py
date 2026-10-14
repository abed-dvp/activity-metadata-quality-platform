import pandas as pd

from src.scoring.quality_impact import (
    build_quality_impact_scores,
    category_impact,
    location_impact,
    priority_band,
    summarize_quality_impact,
)


def test_location_impact_is_conservative_and_bounded():
    assert location_impact("PASS") == 0
    assert location_impact("ADDRESS_QUALITY_REVIEW") == 25
    assert location_impact("ADDRESS_OR_GEOCODER_REVIEW") == 35
    assert location_impact("COORDINATE_MISMATCH_CANDIDATE") == 55


def test_category_impact_uses_conflict_and_uncertainty_not_business_value():
    assert category_impact(pd.Series({
        "is_member": 1,
        "semantic_decision": "member",
        "semantic_confidence": 0.99,
        "provider_error": None,
    })) == 0
    assert category_impact(pd.Series({
        "is_member": 1,
        "semantic_decision": "uncertain",
        "semantic_confidence": 0.5,
        "provider_error": None,
    })) == 20
    assert category_impact(pd.Series({
        "is_member": 1,
        "semantic_decision": "not_member",
        "semantic_confidence": 0.99,
        "provider_error": None,
    })) == 45


def test_unified_score_marks_missing_category_as_partial():
    location = pd.DataFrame([
        {
            "entity_id": "a",
            "name": "A",
            "quality_gate_route": "ADDRESS_QUALITY_REVIEW",
            "likely_bad_field": "address",
        },
        {
            "entity_id": "b",
            "name": "B",
            "quality_gate_route": "PASS",
            "likely_bad_field": "none",
        },
    ])
    category = pd.DataFrame([
        {
            "entity_id": "b",
            "evaluated_category": "nature",
            "is_member": 1,
            "semantic_decision": "uncertain",
            "semantic_confidence": 0.5,
            "provider_error": None,
        }
    ])

    scores = build_quality_impact_scores(location, category)
    a = scores.loc[scores["entity_id"] == "a"].iloc[0]
    b = scores.loc[scores["entity_id"] == "b"].iloc[0]

    assert a["score_status"] == "partial"
    assert a["domain_coverage"] == 0.5
    assert a["quality_impact_score"] == 25
    assert b["score_status"] == "full"
    assert b["quality_impact_score"] == 20
    assert priority_band(50) == "HIGH"

    summary = summarize_quality_impact(scores)
    assert summary["full_score_rows"] == 1
    assert summary["partial_score_rows"] == 1
    assert summary["automatic_action_enabled"] is False
