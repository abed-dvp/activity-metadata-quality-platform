import pandas as pd
import pytest

from src.feedback.closed_loop import (
    build_feedback_learning_events,
    build_regression_cases,
    summarize_closed_loop,
    validate_feedback,
)


def action_queue():
    return pd.DataFrame([
        {
            "entity_id": "a",
            "name": "A",
            "quality_impact_score": 35,
            "score_status": "partial",
            "location_route": "ADDRESS_OR_GEOCODER_REVIEW",
            "action": "HUMAN_REVIEW",
            "action_lane": "EVIDENCE_GAP",
            "downstream_if_confirmed": "FIELD_SPECIFIC_REMEDIATION",
            "auto_flag_internal": True,
        }
    ])


def feedback():
    return pd.DataFrame([
        {
            "feedback_id": "f1",
            "entity_id": "a",
            "domain": "location",
            "feedback_source": "assisted_evidence_review",
            "reviewer_type": "assisted",
            "confirmed_issue": True,
            "confirmed_bad_field": "address",
            "confirmed_root_cause": "ADDRESS_CONTEXT_INCOMPLETE",
            "coordinate_change_required": False,
            "address_change_required": True,
            "human_gold_eligible": False,
            "threshold_calibration_eligible": False,
            "regression_safety_eligible": True,
        }
    ])


def test_assisted_feedback_cannot_calibrate_thresholds():
    bad = feedback()
    bad.loc[0, "threshold_calibration_eligible"] = True
    with pytest.raises(ValueError):
        validate_feedback(bad)


def test_feedback_confirms_address_first_review_and_emits_regression_case():
    events = build_feedback_learning_events(action_queue(), feedback())
    assert events.loc[0, "learning_signal"] == "ADDRESS_FIRST_ROUTING_CONFIRMED"
    assert bool(events.loc[0, "policy_review_alignment"]) is True
    assert bool(events.loc[0, "may_update_thresholds"]) is False

    location = pd.DataFrame([
        {
            "entity_id": "a",
            "name": "A",
            "address": "20 Richmond Rd",
            "geocoder_status": "resolved",
            "reference_display_name": "20 Richmond Road, Leytonstone",
            "distance_m": 26915.4,
            "consistency_decision": "suspicious",
            "quality_gate_route": "ADDRESS_OR_GEOCODER_REVIEW",
            "likely_bad_field": "address_or_reference_match",
        }
    ])
    cases = build_regression_cases(location, events)

    assert len(cases) == 1
    assert cases.loc[0, "expected_route"] == "ADDRESS_OR_GEOCODER_REVIEW"
    assert cases.loc[0, "forbidden_route"] == "COORDINATE_MISMATCH_CANDIDATE"
    assert bool(cases.loc[0, "calibration_use_allowed"]) is False


def test_summary_reports_feedback_coverage_without_claiming_retraining():
    events = build_feedback_learning_events(action_queue(), feedback())
    location = pd.DataFrame([
        {
            "entity_id": "a",
            "name": "A",
            "address": "20 Richmond Rd",
            "geocoder_status": "resolved",
            "reference_display_name": "20 Richmond Road, Leytonstone",
            "distance_m": 26915.4,
            "consistency_decision": "suspicious",
            "quality_gate_route": "ADDRESS_OR_GEOCODER_REVIEW",
            "likely_bad_field": "address_or_reference_match",
        }
    ])
    cases = build_regression_cases(location, events)
    summary = summarize_closed_loop(action_queue(), events, cases)

    assert summary["feedback_rows"] == 1
    assert summary["human_gold_rows"] == 0
    assert summary["regression_cases_emitted"] == 1
    assert summary["retraining_triggered"] is False
    assert summary["production_policy_change_triggered"] is False
