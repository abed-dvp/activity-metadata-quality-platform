from __future__ import annotations

import pandas as pd

REVIEW_REASONS = (
    "UNCERTAIN",
    "HIGH_CONFIDENCE_LABEL_CONFLICT",
    "LABEL_CONFLICT",
)


def _semantic_prediction(series: pd.Series) -> pd.Series:
    return series.map({"member": 1, "not_member": 0})


def build_review_queue(
    calibration: pd.DataFrame,
    high_confidence_threshold: float = 0.90,
) -> pd.DataFrame:
    required = {
        "entity_id", "name", "category", "is_member", "semantic_decision",
        "semantic_confidence", "semantic_reason_codes", "semantic_evidence",
    }
    missing = required - set(calibration.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = calibration.copy()
    df["semantic_prediction"] = _semantic_prediction(df["semantic_decision"])
    conflict = df["semantic_prediction"].notna() & (
        df["semantic_prediction"].astype("Int64") != df["is_member"].astype("Int64")
    )

    def reason(row: pd.Series) -> str | None:
        if row["semantic_decision"] == "uncertain":
            return "UNCERTAIN"
        if bool(row["_conflict"]) and float(row["semantic_confidence"]) >= high_confidence_threshold:
            return "HIGH_CONFIDENCE_LABEL_CONFLICT"
        if bool(row["_conflict"]):
            return "LABEL_CONFLICT"
        return None

    df["_conflict"] = conflict
    df["review_reason"] = df.apply(reason, axis=1)
    queue = df.loc[df["review_reason"].notna()].copy()

    priority_rank = {
        "HIGH_CONFIDENCE_LABEL_CONFLICT": 0,
        "UNCERTAIN": 1,
        "LABEL_CONFLICT": 2,
    }
    queue["review_priority"] = queue["review_reason"].map(priority_rank).astype(int)
    queue["review_case_id"] = (
        queue["entity_id"].astype(str) + "::" + queue["category"].astype(str)
    )
    queue["adjudication_status"] = "PENDING"

    queue = queue.sort_values(
        ["review_priority", "semantic_confidence", "review_case_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    return queue.drop(columns=["_conflict"], errors="ignore")


def review_queue_summary(queue: pd.DataFrame) -> dict:
    return {
        "review_cases": int(len(queue)),
        "by_reason": {
            str(k): int(v)
            for k, v in queue["review_reason"].value_counts().to_dict().items()
        },
        "high_confidence_cases": int((queue["semantic_confidence"] >= 0.90).sum()),
        "categories": sorted(queue["category"].astype(str).unique().tolist()),
    }
