import pandas as pd

from src.demo.end_to_end import build_demo_trace, render_markdown


def test_demo_traces_issue_to_feedback_and_regression_without_side_effects():
    entity_id = "x"

    location = pd.DataFrame([
        {
            "entity_id": entity_id,
            "name": "Example",
            "address": "20 Richmond Rd",
            "latitude": 51.4,
            "longitude": -0.3,
            "geocoder_status": "resolved",
            "distance_m": 26000.0,
            "consistency_decision": "suspicious",
            "quality_gate_route": "ADDRESS_OR_GEOCODER_REVIEW",
            "likely_bad_field": "address_or_reference_match",
            "address_specificity": "street_number",
            "entity_name_match_score": 0.0,
            "automatic_coordinate_overwrite": False,
        }
    ])
    scores = pd.DataFrame([
        {
            "entity_id": entity_id,
            "quality_impact_score": 35,
            "priority_band": "MEDIUM",
            "score_status": "partial",
            "domain_coverage": 0.5,
            "location_impact_score": 35,
            "category_evaluated": False,
            "category_impact_score": 0,
        }
    ])
    actions = pd.DataFrame([
        {
            "entity_id": entity_id,
            "action": "HUMAN_REVIEW",
            "action_lane": "EVIDENCE_GAP",
            "owner": "CONTENT_QUALITY_OPS",
            "auto_flag_internal": True,
            "downstream_if_confirmed": "FIELD_SPECIFIC_REMEDIATION",
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }
    ])
    events = pd.DataFrame([
        {
            "entity_id": entity_id,
            "feedback_source": "assisted_evidence_review",
            "reviewer_type": "assisted",
            "confirmed_issue": True,
            "confirmed_bad_field": "address",
            "confirmed_root_cause": "ADDRESS_CONTEXT_INCOMPLETE",
            "remediation_candidate": "20 Richmond Road, Kingston upon Thames",
            "learning_signal": "ADDRESS_FIRST_ROUTING_CONFIRMED",
            "human_gold_eligible": False,
            "may_update_thresholds": False,
            "metadata_mutation_applied": False,
        }
    ])
    regression = pd.DataFrame([
        {
            "entity_id": entity_id,
            "expected_route": "ADDRESS_OR_GEOCODER_REVIEW",
            "forbidden_route": "COORDINATE_MISMATCH_CANDIDATE",
            "calibration_use_allowed": False,
        }
    ])

    trace = build_demo_trace(
        entity_id, location, scores, actions, events, regression
    )

    assert trace["stage_1_detect"]["distance_m"] == 26000.0
    assert (
        trace["stage_2_quality_gate"]["route"]
        == "ADDRESS_OR_GEOCODER_REVIEW"
    )
    assert trace["stage_3_quality_impact"]["score"] == 35
    assert trace["stage_4_action_policy"]["action"] == "HUMAN_REVIEW"
    assert trace["stage_5_feedback"]["confirmed_bad_field"] == "address"
    assert (
        trace["stage_6_regression"]["forbidden_route"]
        == "COORDINATE_MISMATCH_CANDIDATE"
    )
    assert trace["executive_takeaway"]["learning_loop_closed"] is True
    assert trace["executive_takeaway"]["external_side_effects"] is False

    markdown = render_markdown(trace)
    assert "60-second story" in markdown
    assert "Automatic coordinate overwrite: **False**" in markdown
