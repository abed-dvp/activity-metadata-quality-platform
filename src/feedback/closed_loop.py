from __future__ import annotations

import pandas as pd


REQUIRED_FEEDBACK_COLUMNS = {
    "feedback_id",
    "entity_id",
    "domain",
    "feedback_source",
    "reviewer_type",
    "confirmed_issue",
    "confirmed_bad_field",
    "confirmed_root_cause",
    "coordinate_change_required",
    "address_change_required",
    "human_gold_eligible",
    "threshold_calibration_eligible",
    "regression_safety_eligible",
}


def validate_feedback(feedback: pd.DataFrame) -> None:
    missing = REQUIRED_FEEDBACK_COLUMNS - set(feedback.columns)
    if missing:
        raise ValueError(f"Feedback is missing required columns: {sorted(missing)}")

    if feedback["feedback_id"].duplicated().any():
        raise ValueError("feedback_id must be unique")

    invalid_calibration = feedback[
        feedback["threshold_calibration_eligible"].astype(bool)
        & ~feedback["human_gold_eligible"].astype(bool)
    ]
    if len(invalid_calibration):
        raise ValueError(
            "Only human-gold feedback can be eligible for threshold calibration"
        )


def _learning_signal(row: pd.Series) -> str:
    action = str(row.get("action", ""))
    route = str(row.get("location_route", ""))
    bad_field = str(row.get("confirmed_bad_field", ""))
    coordinate_change = bool(row.get("coordinate_change_required", False))

    if action == "PASS" and bool(row.get("confirmed_issue", False)):
        return "FALSE_PASS"
    if route == "COORDINATE_MISMATCH_CANDIDATE" and not coordinate_change:
        return "FALSE_COORDINATE_CANDIDATE"
    if route == "ADDRESS_OR_GEOCODER_REVIEW" and bad_field == "address":
        return "ADDRESS_FIRST_ROUTING_CONFIRMED"
    if action == "HUMAN_REVIEW" and bool(row.get("confirmed_issue", False)):
        return "REVIEW_ROUTING_CONFIRMED"
    return "NO_POLICY_CHANGE_SIGNAL"


def build_feedback_learning_events(
    action_queue: pd.DataFrame,
    feedback: pd.DataFrame,
) -> pd.DataFrame:
    validate_feedback(feedback)

    merged = feedback.merge(
        action_queue[
            [
                "entity_id",
                "name",
                "quality_impact_score",
                "score_status",
                "location_route",
                "action",
                "action_lane",
                "downstream_if_confirmed",
                "auto_flag_internal",
            ]
        ],
        on="entity_id",
        how="left",
        validate="many_to_one",
    )

    merged["queue_match"] = merged["action"].notna()
    merged["policy_review_alignment"] = (
        merged["action"].eq("HUMAN_REVIEW")
        & merged["confirmed_issue"].astype(bool)
    )
    merged["learning_signal"] = merged.apply(_learning_signal, axis=1)
    merged["may_update_thresholds"] = (
        merged["human_gold_eligible"].astype(bool)
        & merged["threshold_calibration_eligible"].astype(bool)
    )
    merged["may_create_regression_case"] = merged["regression_safety_eligible"].astype(bool)
    merged["metadata_mutation_applied"] = False
    merged["supplier_contact_applied"] = False
    return merged


def build_regression_cases(
    gated_location: pd.DataFrame,
    learning_events: pd.DataFrame,
) -> pd.DataFrame:
    eligible = learning_events[
        learning_events["may_create_regression_case"].astype(bool)
    ].copy()

    fixtures = gated_location[
        [
            "entity_id",
            "name",
            "address",
            "geocoder_status",
            "reference_display_name",
            "distance_m",
            "consistency_decision",
            "quality_gate_route",
            "likely_bad_field",
        ]
    ].copy()

    cases = eligible.merge(fixtures, on="entity_id", how="left", validate="many_to_one")
    cases["expected_route"] = cases["quality_gate_route"]
    cases["forbidden_route"] = cases.apply(
        lambda row: (
            "COORDINATE_MISMATCH_CANDIDATE"
            if not bool(row["coordinate_change_required"])
            else ""
        ),
        axis=1,
    )
    cases["calibration_use_allowed"] = cases["may_update_thresholds"].astype(bool)

    keep = [
        "feedback_id",
        "entity_id",
        "name_y",
        "feedback_source",
        "reviewer_type",
        "confirmed_bad_field",
        "confirmed_root_cause",
        "address",
        "geocoder_status",
        "reference_display_name",
        "distance_m",
        "consistency_decision",
        "expected_route",
        "forbidden_route",
        "calibration_use_allowed",
    ]
    out = cases[keep].rename(columns={"name_y": "name"})
    return out.sort_values(["entity_id", "feedback_id"]).reset_index(drop=True)


def summarize_closed_loop(
    action_queue: pd.DataFrame,
    learning_events: pd.DataFrame,
    regression_cases: pd.DataFrame,
) -> dict:
    human_review_rows = int(action_queue["action"].eq("HUMAN_REVIEW").sum())
    feedback_rows = int(len(learning_events))
    human_gold_rows = int(learning_events["human_gold_eligible"].astype(bool).sum())
    assisted_rows = feedback_rows - human_gold_rows

    return {
        "review_queue_human_review_rows": human_review_rows,
        "feedback_rows": feedback_rows,
        "feedback_coverage_of_human_review_queue": (
            feedback_rows / human_review_rows if human_review_rows else 0.0
        ),
        "feedback_source_counts": {
            str(k): int(v)
            for k, v in learning_events["feedback_source"].value_counts().sort_index().to_dict().items()
        },
        "human_gold_rows": human_gold_rows,
        "assisted_feedback_rows": assisted_rows,
        "confirmed_issue_rows": int(learning_events["confirmed_issue"].astype(bool).sum()),
        "confirmed_address_defects": int(
            learning_events["confirmed_bad_field"].eq("address").sum()
        ),
        "confirmed_coordinate_changes_required": int(
            learning_events["coordinate_change_required"].astype(bool).sum()
        ),
        "policy_review_alignment_rows": int(
            learning_events["policy_review_alignment"].astype(bool).sum()
        ),
        "false_pass_rows": int(learning_events["learning_signal"].eq("FALSE_PASS").sum()),
        "false_coordinate_candidate_rows": int(
            learning_events["learning_signal"].eq("FALSE_COORDINATE_CANDIDATE").sum()
        ),
        "regression_cases_emitted": int(len(regression_cases)),
        "threshold_calibration_eligible_rows": int(
            learning_events["may_update_thresholds"].astype(bool).sum()
        ),
        "metadata_mutations_applied": 0,
        "supplier_contacts_applied": 0,
        "retraining_triggered": False,
        "production_policy_change_triggered": False,
        "governance_note": (
            "Assisted evidence review may create regression safety cases but cannot calibrate "
            "thresholds or act as independent human gold."
        ),
    }
