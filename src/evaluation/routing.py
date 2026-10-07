from __future__ import annotations

import pandas as pd


def route_semantic_decisions(
    df: pd.DataFrame,
    member_threshold: float = 0.95,
    not_member_threshold: float = 0.95,
) -> pd.DataFrame:
    required = {"semantic_decision", "semantic_confidence"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()

    def route(row: pd.Series) -> str:
        decision = row["semantic_decision"]
        confidence = float(row["semantic_confidence"])
        if decision == "uncertain":
            return "HUMAN_REVIEW"
        if decision == "member" and confidence >= member_threshold:
            return "AUTO_MEMBER"
        if decision == "not_member" and confidence >= not_member_threshold:
            return "AUTO_NOT_MEMBER"
        return "HUMAN_REVIEW"

    out["route"] = out.apply(route, axis=1)
    return out


def threshold_sweep(
    df: pd.DataFrame,
    thresholds=(0.80, 0.85, 0.90, 0.95, 0.98, 0.99),
) -> pd.DataFrame:
    required = {"is_member", "semantic_decision", "semantic_confidence"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rows: list[dict] = []
    for threshold in thresholds:
        routed = route_semantic_decisions(df, threshold, threshold)
        auto = routed.loc[routed["route"] != "HUMAN_REVIEW"].copy()
        auto["routed_prediction"] = auto["route"].map(
            {"AUTO_MEMBER": 1, "AUTO_NOT_MEMBER": 0}
        )
        correct = int(
            (auto["routed_prediction"] == auto["is_member"]).sum()
        ) if len(auto) else 0
        errors = int(len(auto) - correct)

        rows.append({
            "threshold": threshold,
            "rows": int(len(df)),
            "auto_rows": int(len(auto)),
            "review_rows": int(len(df) - len(auto)),
            "auto_coverage": float(len(auto) / len(df)) if len(df) else 0.0,
            "auto_accuracy": float(correct / len(auto)) if len(auto) else 0.0,
            "auto_error_rate": float(errors / len(auto)) if len(auto) else 0.0,
            "auto_errors": errors,
        })

    return pd.DataFrame(rows)
