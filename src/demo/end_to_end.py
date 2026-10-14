from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ENTITY_ID = "london_poi_42079.0"
DEFAULT_LOCATION = ROOT / "reports" / "location" / "semantic" / "location_gated_results.csv"
DEFAULT_SCORES = ROOT / "reports" / "impact" / "quality_impact_scores.csv"
DEFAULT_ACTIONS = ROOT / "reports" / "impact" / "quality_action_queue.csv"
DEFAULT_EVENTS = ROOT / "reports" / "feedback" / "learning_events.csv"
DEFAULT_REGRESSION = ROOT / "reports" / "feedback" / "closed_loop_regression_cases.csv"


def _single(df: pd.DataFrame, entity_id: str, source_name: str) -> pd.Series:
    match = df.loc[df["entity_id"].astype(str).eq(str(entity_id))]
    if len(match) != 1:
        raise ValueError(
            f"Expected exactly one {source_name} row for {entity_id}, found {len(match)}"
        )
    return match.iloc[0]


def _optional_single(df: pd.DataFrame, entity_id: str) -> pd.Series | None:
    match = df.loc[df["entity_id"].astype(str).eq(str(entity_id))]
    if match.empty:
        return None
    if len(match) != 1:
        raise ValueError(f"Expected at most one row for {entity_id}, found {len(match)}")
    return match.iloc[0]


def _clean(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def build_demo_trace(
    entity_id: str,
    location: pd.DataFrame,
    scores: pd.DataFrame,
    actions: pd.DataFrame,
    events: pd.DataFrame,
    regression: pd.DataFrame,
) -> dict:
    loc = _single(location, entity_id, "location")
    score = _single(scores, entity_id, "score")
    action = _single(actions, entity_id, "action")
    event = _optional_single(events, entity_id)
    case = _optional_single(regression, entity_id)

    trace = {
        "demo_version": "end_to_end_v1",
        "entity_id": str(entity_id),
        "listing": {
            "name": _clean(loc.get("name")),
            "address": _clean(loc.get("address")),
            "latitude": _clean(loc.get("latitude")),
            "longitude": _clean(loc.get("longitude")),
        },
        "stage_1_detect": {
            "signal": "address_coordinate_disagreement",
            "geocoder_status": _clean(loc.get("geocoder_status")),
            "distance_m": _clean(loc.get("distance_m")),
            "raw_consistency_decision": _clean(loc.get("consistency_decision")),
        },
        "stage_2_quality_gate": {
            "route": _clean(loc.get("quality_gate_route")),
            "likely_bad_field": _clean(loc.get("likely_bad_field")),
            "address_specificity": _clean(loc.get("address_specificity")),
            "entity_name_match_score": _clean(loc.get("entity_name_match_score")),
            "automatic_coordinate_overwrite": bool(
                loc.get("automatic_coordinate_overwrite", False)
            ),
        },
        "stage_3_quality_impact": {
            "score": int(score["quality_impact_score"]),
            "priority_band": _clean(score.get("priority_band")),
            "score_status": _clean(score.get("score_status")),
            "domain_coverage": float(score.get("domain_coverage", 0.0)),
            "location_impact_score": int(score.get("location_impact_score", 0)),
            "category_evaluated": bool(score.get("category_evaluated", False)),
            "category_impact_score": int(score.get("category_impact_score", 0)),
        },
        "stage_4_action_policy": {
            "action": _clean(action.get("action")),
            "lane": _clean(action.get("action_lane")),
            "owner": _clean(action.get("owner")),
            "auto_flag_internal": bool(action.get("auto_flag_internal", False)),
            "downstream_if_confirmed": _clean(action.get("downstream_if_confirmed")),
            "supplier_contact_enabled": bool(
                action.get("supplier_contact_enabled", False)
            ),
            "metadata_mutation_enabled": bool(
                action.get("metadata_mutation_enabled", False)
            ),
        },
        "stage_5_feedback": None,
        "stage_6_regression": None,
    }

    if event is not None:
        trace["stage_5_feedback"] = {
            "feedback_source": _clean(event.get("feedback_source")),
            "reviewer_type": _clean(event.get("reviewer_type")),
            "confirmed_issue": bool(event.get("confirmed_issue", False)),
            "confirmed_bad_field": _clean(event.get("confirmed_bad_field")),
            "confirmed_root_cause": _clean(event.get("confirmed_root_cause")),
            "remediation_candidate": _clean(event.get("remediation_candidate")),
            "learning_signal": _clean(event.get("learning_signal")),
            "human_gold_eligible": bool(event.get("human_gold_eligible", False)),
            "may_update_thresholds": bool(event.get("may_update_thresholds", False)),
            "metadata_mutation_applied": bool(
                event.get("metadata_mutation_applied", False)
            ),
        }

    if case is not None:
        trace["stage_6_regression"] = {
            "expected_route": _clean(case.get("expected_route")),
            "forbidden_route": _clean(case.get("forbidden_route")),
            "calibration_use_allowed": bool(
                case.get("calibration_use_allowed", False)
            ),
        }

    feedback = trace["stage_5_feedback"]
    regression_stage = trace["stage_6_regression"]
    trace["executive_takeaway"] = {
        "detected_large_disagreement": float(
            trace["stage_1_detect"]["distance_m"] or 0
        ) > 1500,
        "avoided_automatic_bad_pin_claim": (
            trace["stage_2_quality_gate"]["route"]
            != "COORDINATE_MISMATCH_CANDIDATE"
        ),
        "human_review_confirmed_address_issue": bool(
            feedback and feedback["confirmed_bad_field"] == "address"
        ),
        "learning_loop_closed": bool(regression_stage),
        "external_side_effects": False,
        "message": (
            "The platform detected a large location inconsistency, used quality gates "
            "to avoid a false bad-pin conclusion, routed the case to review, captured "
            "the confirmed address defect, and converted the outcome into a regression "
            "safety case without changing supplier metadata automatically."
        ),
    }
    return trace


def render_markdown(trace: dict) -> str:
    listing = trace["listing"]
    detect = trace["stage_1_detect"]
    gate = trace["stage_2_quality_gate"]
    score = trace["stage_3_quality_impact"]
    action = trace["stage_4_action_policy"]
    feedback = trace["stage_5_feedback"]
    regression = trace["stage_6_regression"]

    feedback_lines = (
        [
            f"- Confirmed bad field: **{feedback['confirmed_bad_field']}**",
            f"- Root cause: **{feedback['confirmed_root_cause']}**",
            f"- Remediation candidate: `{feedback['remediation_candidate']}`",
            f"- Human gold eligible: **{feedback['human_gold_eligible']}**",
        ]
        if feedback
        else ["- No adjudicated feedback is available yet."]
    )

    regression_lines = (
        [
            f"- Expected safe route: `{regression['expected_route']}`",
            f"- Forbidden regression: `{regression['forbidden_route']}`",
            f"- Allowed for threshold calibration: **{regression['calibration_use_allowed']}**",
        ]
        if regression
        else ["- No regression case is available yet."]
    )

    return "\n".join(
        [
            "# End-to-end executive demo",
            "",
            "## 60-second story",
            "",
            trace["executive_takeaway"]["message"],
            "",
            "## Listing",
            "",
            f"- **{listing['name']}**",
            f"- Source address: `{listing['address']}`",
            f"- Source coordinates: `{listing['latitude']}, {listing['longitude']}`",
            "",
            "## 1. Detect",
            "",
            f"- Address ↔ coordinate disagreement: **{detect['distance_m']} m**",
            f"- Raw diagnostic: `{detect['raw_consistency_decision']}`",
            "",
            "## 2. Quality gate",
            "",
            f"- Route: `{gate['route']}`",
            f"- Likely bad field: `{gate['likely_bad_field']}`",
            f"- Automatic coordinate overwrite: **{gate['automatic_coordinate_overwrite']}**",
            "",
            "## 3. Quality Impact Score",
            "",
            f"- Score: **{score['score']}/100**",
            f"- Priority: **{score['priority_band']}**",
            f"- Coverage: **{score['score_status']} ({score['domain_coverage']:.1f})**",
            "",
            "## 4. Action policy",
            "",
            f"- Action: `{action['action']}`",
            f"- Lane: `{action['lane']}`",
            f"- Internal auto-flag: **{action['auto_flag_internal']}**",
            f"- Supplier contact: **{action['supplier_contact_enabled']}**",
            f"- Metadata mutation: **{action['metadata_mutation_enabled']}**",
            "",
            "## 5. Review feedback",
            "",
            *feedback_lines,
            "",
            "## 6. Closed-loop regression",
            "",
            *regression_lines,
            "",
            "## Why this matters",
            "",
            "A naive pipeline would have treated a 26.9 km geocoder disagreement as a bad pin. "
            "This pipeline separates detection from diagnosis, keeps external side effects disabled, "
            "and turns reviewed mistakes into reusable regression evidence.",
            "",
        ]
    )


def run_demo(
    entity_id: str = DEFAULT_ENTITY_ID,
    location_path: Path = DEFAULT_LOCATION,
    scores_path: Path = DEFAULT_SCORES,
    actions_path: Path = DEFAULT_ACTIONS,
    events_path: Path = DEFAULT_EVENTS,
    regression_path: Path = DEFAULT_REGRESSION,
) -> dict:
    return build_demo_trace(
        entity_id=entity_id,
        location=pd.read_csv(location_path),
        scores=pd.read_csv(scores_path),
        actions=pd.read_csv(actions_path),
        events=pd.read_csv(events_path),
        regression=pd.read_csv(regression_path),
    )


def write_demo(trace: dict, json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(trace), encoding="utf-8")
