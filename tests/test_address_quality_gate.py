import pandas as pd

from src.quality.address_gate import (
    address_specificity,
    entity_name_match_score,
    route_location_quality,
)


def test_entity_match_score_detects_reference_entity_evidence():
    assert entity_name_match_score("The Ship Inn", "The Ship, 290 Westferry Road") >= 0.5
    assert entity_name_match_score("The Corrib Rest", "82 Salisbury Road, High Barnet") == 0.0


def test_low_specificity_address_routes_to_address_review():
    row = pd.Series({
        "name": "Italian Gardens",
        "address": "London, United Kingdom",
        "geocoder_status": "resolved",
        "reference_display_name": "Greater London",
        "consistency_decision": "suspicious",
    })
    result = route_location_quality(row)
    assert result["quality_gate_route"] == "ADDRESS_QUALITY_REVIEW"
    assert result["likely_bad_field"] == "address"


def test_acorn_regression_does_not_become_bad_pin():
    row = pd.Series({
        "name": "Acorn 20/20",
        "address": "20 Richmond Rd",
        "geocoder_status": "resolved",
        "reference_display_name": "20 Richmond Road, Leytonstone, London",
        "consistency_decision": "suspicious",
    })
    result = route_location_quality(row)
    assert result["quality_gate_route"] == "ADDRESS_OR_GEOCODER_REVIEW"
    assert result["automatic_coordinate_overwrite"] is False


def test_corrib_regression_does_not_become_bad_pin():
    row = pd.Series({
        "name": "The Corrib Rest",
        "address": "82 Salisbury Rd",
        "geocoder_status": "resolved",
        "reference_display_name": "82 Salisbury Road, High Barnet",
        "consistency_decision": "suspicious",
    })
    result = route_location_quality(row)
    assert result["quality_gate_route"] == "ADDRESS_OR_GEOCODER_REVIEW"
    assert result["automatic_coordinate_overwrite"] is False


def test_suspicious_with_entity_evidence_can_be_mismatch_candidate():
    row = pd.Series({
        "name": "Example Venue",
        "address": "10 Example Street, London",
        "geocoder_status": "resolved",
        "reference_display_name": "Example Venue, 10 Example Street, London",
        "consistency_decision": "suspicious",
    })
    result = route_location_quality(row)
    assert result["quality_gate_route"] == "COORDINATE_MISMATCH_CANDIDATE"
