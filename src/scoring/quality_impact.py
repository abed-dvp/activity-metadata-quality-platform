from __future__ import annotations

import pandas as pd


LOCATION_IMPACT = {
    "PASS": 0,
    "BOUNDARY_REVIEW": 15,
    "GEOCODER_UNRESOLVED_REVIEW": 20,
    "ADDRESS_QUALITY_REVIEW": 25,
    "ADDRESS_OR_GEOCODER_REVIEW": 35,
    "COORDINATE_MISMATCH_CANDIDATE": 55,
    "HUMAN_REVIEW": 20,
}


def location_impact(route: object) -> int:
    return int(LOCATION_IMPACT.get(str(route), 20))


def category_impact(row: pd.Series | dict) -> int:
    get = row.get
    provider_error = get("provider_error")
    if provider_error is not None and not pd.isna(provider_error) and str(provider_error).strip():
        return 20

    decision = str(get("semantic_decision", ""))
    confidence = float(get("semantic_confidence", 0.0) or 0.0)
    reference = int(get("is_member", 0))
    expected = "member" if reference == 1 else "not_member"

    if decision == "uncertain":
        return 20

    agrees = decision == expected
    if agrees:
        if confidence >= 0.98:
            return 0
        if confidence >= 0.90:
            return 5
        return 10

    if confidence >= 0.98:
        return 45
    if confidence >= 0.90:
        return 35
    return 25


def priority_band(score: int) -> str:
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "NONE"


def aggregate_category_evidence(category_rows: pd.DataFrame) -> dict:
    if category_rows.empty:
        return {
            "category_impact_score": 0,
            "category_evaluated": False,
            "categories_evaluated": "",
            "category_evaluation_count": 0,
            "category_issue_count": 0,
        }

    impacts = category_rows.apply(category_impact, axis=1)
    return {
        "category_impact_score": int(impacts.max()),
        "category_evaluated": True,
        "categories_evaluated": ",".join(sorted(category_rows["evaluated_category"].astype(str).unique())),
        "category_evaluation_count": int(len(category_rows)),
        "category_issue_count": int((impacts > 0).sum()),
    }


def build_quality_impact_scores(
    location_rows: pd.DataFrame,
    category_rows: pd.DataFrame,
) -> pd.DataFrame:
    output: list[dict] = []

    grouped = {
        str(entity_id): group.copy()
        for entity_id, group in category_rows.groupby(category_rows["entity_id"].astype(str))
    }

    for _, row in location_rows.iterrows():
        entity_id = str(row["entity_id"])
        loc_score = location_impact(row.get("quality_gate_route"))
        category = aggregate_category_evidence(
            grouped.get(entity_id, pd.DataFrame(columns=category_rows.columns))
        )
        observed = loc_score + int(category["category_impact_score"])
        coverage = 1.0 if category["category_evaluated"] else 0.5

        output.append(
            {
                "entity_id": entity_id,
                "name": row.get("name"),
                "quality_impact_score": int(observed),
                "priority_band": priority_band(int(observed)),
                "score_status": "full" if coverage == 1.0 else "partial",
                "domain_coverage": coverage,
                "location_impact_score": loc_score,
                "location_route": row.get("quality_gate_route"),
                "likely_bad_field": row.get("likely_bad_field"),
                **category,
                "automatic_action_enabled": False,
            }
        )

    return pd.DataFrame(output).sort_values(
        ["score_status", "quality_impact_score", "entity_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def summarize_quality_impact(scores: pd.DataFrame) -> dict:
    full = scores[scores["score_status"].eq("full")]
    partial = scores[scores["score_status"].eq("partial")]
    return {
        "rows": int(len(scores)),
        "full_score_rows": int(len(full)),
        "partial_score_rows": int(len(partial)),
        "full_score_priority_bands": {
            str(k): int(v)
            for k, v in full["priority_band"].value_counts().sort_index().to_dict().items()
        },
        "partial_score_priority_bands": {
            str(k): int(v)
            for k, v in partial["priority_band"].value_counts().sort_index().to_dict().items()
        },
        "max_full_quality_impact_score": int(full["quality_impact_score"].max()) if len(full) else None,
        "automatic_action_enabled": False,
        "score_semantics": "0-100 observed review-priority impact; higher means more urgent quality review.",
        "important_caveat": (
            "Weights are heuristic prioritization weights, not calibrated revenue, conversion, "
            "or causal business-impact estimates. Partial scores must not be ranked directly "
            "against full scores."
        ),
    }
