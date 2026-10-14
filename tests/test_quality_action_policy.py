import pandas as pd

from src.policy.quality_action_policy import (
    apply_action_policy,
    recommended_action,
    summarize_action_policy,
)


def base_row(**overrides):
    row = {
        "entity_id": "x",
        "name": "Example",
        "quality_impact_score": 0,
        "priority_band": "NONE",
        "score_status": "full",
        "domain_coverage": 1.0,
        "location_route": "PASS",
        "likely_bad_field": "none",
        "category_issue_count": 0,
    }
    row.update(overrides)
    return pd.Series(row)


def test_full_clean_row_passes_without_external_action():
    result = recommended_action(base_row())
    assert result["action"] == "PASS"
    assert result["supplier_contact_enabled"] is False
    assert result["metadata_mutation_enabled"] is False


def test_partial_clean_row_needs_more_evidence_not_pass():
    result = recommended_action(base_row(score_status="partial", domain_coverage=0.5))
    assert result["action"] == "NEED_MORE_EVIDENCE"


def test_address_issue_is_supplier_fix_candidate_only_after_review():
    result = recommended_action(
        base_row(
            quality_impact_score=35,
            priority_band="MEDIUM",
            location_route="ADDRESS_QUALITY_REVIEW",
            likely_bad_field="address",
        )
    )
    assert result["action"] == "HUMAN_REVIEW"
    assert result["action_lane"] == "SUPPLIER_CONTENT"
    assert result["downstream_if_confirmed"] == "SUPPLIER_FIX_REQUEST_CANDIDATE"
    assert result["auto_flag_internal"] is True
    assert result["supplier_contact_enabled"] is False


def test_category_issue_routes_to_taxonomy_review():
    result = recommended_action(
        base_row(
            quality_impact_score=10,
            priority_band="LOW",
            category_issue_count=1,
        )
    )
    assert result["action_lane"] == "CATEGORY"
    assert result["downstream_if_confirmed"] == "CATEGORY_FIX_CANDIDATE"


def test_action_summary_keeps_external_actions_disabled():
    scores = pd.DataFrame([
        base_row().to_dict(),
        base_row(
            entity_id="p",
            score_status="partial",
            domain_coverage=0.5,
        ).to_dict(),
        base_row(
            entity_id="a",
            quality_impact_score=30,
            priority_band="MEDIUM",
            location_route="ADDRESS_QUALITY_REVIEW",
            likely_bad_field="address",
        ).to_dict(),
    ])
    actions = apply_action_policy(scores)
    summary = summarize_action_policy(actions)

    assert summary["rows"] == 3
    assert summary["internal_auto_flags"] == 1
    assert summary["supplier_contact_enabled"] is False
    assert summary["metadata_mutation_enabled"] is False
    assert summary["production_enabled"] is False
