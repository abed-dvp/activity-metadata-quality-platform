from __future__ import annotations

import pandas as pd


def recommended_action(row: pd.Series | dict) -> dict:
    get = row.get
    status = str(get("score_status", "partial"))
    score = int(float(get("quality_impact_score", 0) or 0))
    band = str(get("priority_band", "NONE"))
    location_route = str(get("location_route", ""))
    likely_bad_field = str(get("likely_bad_field", "unknown"))
    category_issue_count = int(float(get("category_issue_count", 0) or 0))

    # Missing domain evidence is never interpreted as confirmed good quality.
    if status != "full":
        if score == 0:
            return {
                "action": "NEED_MORE_EVIDENCE",
                "action_lane": "COVERAGE",
                "owner": "QUALITY_PLATFORM",
                "reason": "Only partial domain coverage is available.",
                "downstream_if_confirmed": "PASS_OR_REVIEW",
                "auto_flag_internal": False,
                "supplier_contact_enabled": False,
                "metadata_mutation_enabled": False,
            }
        return {
            "action": "HUMAN_REVIEW",
            "action_lane": "EVIDENCE_GAP",
            "owner": "CONTENT_QUALITY_OPS",
            "reason": "Observed issue exists but the unified score has partial domain coverage.",
            "downstream_if_confirmed": "FIELD_SPECIFIC_REMEDIATION",
            "auto_flag_internal": True,
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }

    if score == 0:
        return {
            "action": "PASS",
            "action_lane": "NONE",
            "owner": "SYSTEM",
            "reason": "No observed issue in the evaluated Category and Location domains.",
            "downstream_if_confirmed": "NONE",
            "auto_flag_internal": False,
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }

    if location_route == "COORDINATE_MISMATCH_CANDIDATE":
        return {
            "action": "HUMAN_REVIEW",
            "action_lane": "LOCATION_COORDINATE",
            "owner": "CONTENT_QUALITY_OPS",
            "reason": "Coordinate mismatch candidate requires independent confirmation before any pin change.",
            "downstream_if_confirmed": "INTERNAL_COORDINATE_FIX_CANDIDATE",
            "auto_flag_internal": True,
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }

    if location_route == "ADDRESS_QUALITY_REVIEW" and likely_bad_field == "address":
        return {
            "action": "HUMAN_REVIEW",
            "action_lane": "SUPPLIER_CONTENT",
            "owner": "CONTENT_QUALITY_OPS",
            "reason": "Address-quality evidence should be verified before requesting supplier correction.",
            "downstream_if_confirmed": "SUPPLIER_FIX_REQUEST_CANDIDATE",
            "auto_flag_internal": band in {"MEDIUM", "HIGH"},
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }

    if location_route in {
        "GEOCODER_UNRESOLVED_REVIEW",
        "ADDRESS_OR_GEOCODER_REVIEW",
        "BOUNDARY_REVIEW",
    }:
        return {
            "action": "HUMAN_REVIEW",
            "action_lane": "LOCATION_EVIDENCE",
            "owner": "CONTENT_QUALITY_OPS",
            "reason": "Location evidence is ambiguous or unresolved; gather stronger evidence before remediation.",
            "downstream_if_confirmed": "FIELD_SPECIFIC_REMEDIATION",
            "auto_flag_internal": band in {"MEDIUM", "HIGH"},
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }

    if category_issue_count > 0:
        return {
            "action": "HUMAN_REVIEW",
            "action_lane": "CATEGORY",
            "owner": "TAXONOMY_OR_CONTENT_OPS",
            "reason": "Category evidence needs ontology/catalog review before changing classification.",
            "downstream_if_confirmed": "CATEGORY_FIX_CANDIDATE",
            "auto_flag_internal": band in {"MEDIUM", "HIGH"},
            "supplier_contact_enabled": False,
            "metadata_mutation_enabled": False,
        }

    return {
        "action": "HUMAN_REVIEW",
        "action_lane": "GENERAL_QUALITY",
        "owner": "CONTENT_QUALITY_OPS",
        "reason": "Non-zero quality impact requires review but does not map to a narrower remediation lane.",
        "downstream_if_confirmed": "FIELD_SPECIFIC_REMEDIATION",
        "auto_flag_internal": band in {"MEDIUM", "HIGH"},
        "supplier_contact_enabled": False,
        "metadata_mutation_enabled": False,
    }


def apply_action_policy(scores: pd.DataFrame) -> pd.DataFrame:
    policy = scores.apply(lambda row: pd.Series(recommended_action(row)), axis=1)
    out = pd.concat([scores.reset_index(drop=True), policy.reset_index(drop=True)], axis=1)

    action_order = {
        "HUMAN_REVIEW": 0,
        "NEED_MORE_EVIDENCE": 1,
        "PASS": 2,
    }
    out["_action_order"] = out["action"].map(action_order).fillna(9)
    out = out.sort_values(
        ["_action_order", "auto_flag_internal", "quality_impact_score", "entity_id"],
        ascending=[True, False, False, True],
    ).drop(columns=["_action_order"]).reset_index(drop=True)
    return out


def summarize_action_policy(actions: pd.DataFrame) -> dict:
    full = actions[actions["score_status"].eq("full")]
    partial = actions[actions["score_status"].eq("partial")]
    return {
        "rows": int(len(actions)),
        "actions": {
            str(k): int(v)
            for k, v in actions["action"].value_counts().sort_index().to_dict().items()
        },
        "action_lanes": {
            str(k): int(v)
            for k, v in actions["action_lane"].value_counts().sort_index().to_dict().items()
        },
        "internal_auto_flags": int(actions["auto_flag_internal"].astype(bool).sum()),
        "full_rows_pass": int((full["action"] == "PASS").sum()),
        "full_rows_human_review": int((full["action"] == "HUMAN_REVIEW").sum()),
        "partial_rows_need_more_evidence": int((partial["action"] == "NEED_MORE_EVIDENCE").sum()),
        "partial_rows_human_review": int((partial["action"] == "HUMAN_REVIEW").sum()),
        "supplier_fix_request_candidates_after_confirmation": int(
            (actions["downstream_if_confirmed"] == "SUPPLIER_FIX_REQUEST_CANDIDATE").sum()
        ),
        "supplier_contact_enabled": False,
        "metadata_mutation_enabled": False,
        "production_enabled": False,
        "policy_statement": (
            "The system may auto-flag records internally for prioritized human review. "
            "Supplier contact and metadata mutation remain disabled."
        ),
    }
