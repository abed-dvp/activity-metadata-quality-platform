from __future__ import annotations

import pandas as pd


def build_adjudicated_gold(reviewed_queue: pd.DataFrame) -> pd.DataFrame:
    required = {
        "review_case_id", "entity_id", "category", "is_member",
        "reviewer_label", "reviewer_confidence", "resolution_type",
    }
    missing = required - set(reviewed_queue.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    reviewed = reviewed_queue.loc[reviewed_queue["reviewer_label"].notna()].copy()
    reviewed["adjudicated_label"] = reviewed["reviewer_label"].map(
        {"member": 1, "not_member": 0, "ambiguous": pd.NA}
    ).astype("Int64")
    reviewed["gold_status"] = reviewed["reviewer_label"].map(
        {"member": "ADJUDICATED", "not_member": "ADJUDICATED", "ambiguous": "AMBIGUOUS"}
    )
    reviewed["label_origin"] = "human_adjudication"

    cols = [
        "review_case_id", "entity_id", "name", "category", "is_member",
        "adjudicated_label", "gold_status", "reviewer_confidence",
        "resolution_type", "reviewer_notes", "reviewer_id", "reviewed_at",
        "label_origin",
    ]
    return reviewed[[c for c in cols if c in reviewed.columns]]


def build_regression_set(reviewed_queue: pd.DataFrame) -> pd.DataFrame:
    gold = build_adjudicated_gold(reviewed_queue)
    accepted_ids = set(
        gold.loc[gold["gold_status"] == "ADJUDICATED", "review_case_id"]
    )
    source = reviewed_queue.loc[
        reviewed_queue["review_case_id"].isin(accepted_ids)
    ].copy()
    source["expected_label"] = source["reviewer_label"].map(
        {"member": 1, "not_member": 0}
    ).astype("Int64")
    source["case_source"] = "human_adjudicated_phase4"

    cols = [
        "review_case_id", "entity_id", "name", "source_category", "address",
        "details", "review_text", "category", "expected_label", "case_source",
        "resolution_type", "reviewer_confidence",
    ]
    return source[[c for c in cols if c in source.columns]]
