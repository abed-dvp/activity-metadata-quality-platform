from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


DEFAULT_THRESHOLDS = (0.80, 0.85, 0.90, 0.95, 0.98, 0.99)


def route_asymmetric(
    df: pd.DataFrame,
    member_threshold: float,
    not_member_threshold: float,
) -> pd.DataFrame:
    required = {"semantic_decision", "semantic_confidence"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()
    member = (
        out["semantic_decision"].eq("member")
        & out["semantic_confidence"].astype(float).ge(member_threshold)
    )
    not_member = (
        out["semantic_decision"].eq("not_member")
        & out["semantic_confidence"].astype(float).ge(not_member_threshold)
    )

    out["route"] = "HUMAN_REVIEW"
    out.loc[member, "route"] = "AUTO_MEMBER"
    out.loc[not_member, "route"] = "AUTO_NOT_MEMBER"

    if "provider_error" in out.columns:
        out.loc[out["provider_error"].notna(), "route"] = "HUMAN_REVIEW"

    return out


def lane_threshold_validation(
    representative: pd.DataFrame,
    positive_diagnostic: pd.DataFrame,
    assisted_overrides: dict[str, int] | None = None,
    thresholds: Iterable[float] = DEFAULT_THRESHOLDS,
) -> pd.DataFrame:
    required = {"entity_id", "is_member", "semantic_decision", "semantic_confidence"}
    for name, df in (
        ("representative", representative),
        ("positive_diagnostic", positive_diagnostic),
    ):
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{name} missing required columns: {sorted(missing)}")

    overrides = {str(k): int(v) for k, v in (assisted_overrides or {}).items()}
    rep = representative.copy()
    pos = positive_diagnostic.copy()
    rep["assisted_reference"] = rep["is_member"].astype(int)
    pos["assisted_reference"] = pos["is_member"].astype(int)

    for df in (rep, pos):
        ids = df["entity_id"].astype(str)
        mask = ids.isin(overrides)
        df.loc[mask, "assisted_reference"] = ids.loc[mask].map(overrides).astype(int)

    rows: list[dict] = []
    for threshold in thresholds:
        member_lane = rep.loc[
            rep["semantic_decision"].eq("member")
            & rep["semantic_confidence"].astype(float).ge(threshold)
        ]
        not_member_lane = rep.loc[
            rep["semantic_decision"].eq("not_member")
            & rep["semantic_confidence"].astype(float).ge(threshold)
        ]
        public_positive_rejects = pos.loc[
            pos["semantic_decision"].eq("not_member")
            & pos["semantic_confidence"].astype(float).ge(threshold)
        ]

        rows.append(
            {
                "threshold": float(threshold),
                "auto_member_rows": int(len(member_lane)),
                "auto_member_public_errors": int(
                    member_lane["is_member"].astype(int).eq(0).sum()
                ),
                "auto_member_assisted_errors": int(
                    member_lane["assisted_reference"].astype(int).eq(0).sum()
                ),
                "auto_not_member_rows_representative": int(len(not_member_lane)),
                "auto_not_member_public_errors_representative": int(
                    not_member_lane["is_member"].astype(int).eq(1).sum()
                ),
                "public_positive_diagnostic_auto_rejects": int(
                    len(public_positive_rejects)
                ),
                "assisted_positive_diagnostic_auto_rejects": int(
                    public_positive_rejects["assisted_reference"].astype(int).eq(1).sum()
                ),
            }
        )

    return pd.DataFrame(rows)


def select_safety_constrained_thresholds(validation: pd.DataFrame) -> dict[str, float]:
    member_candidates = validation.loc[
        validation["auto_member_public_errors"].eq(0)
    ].sort_values("threshold")
    not_member_candidates = validation.loc[
        validation["public_positive_diagnostic_auto_rejects"].eq(0)
    ].sort_values("threshold")

    if member_candidates.empty:
        raise ValueError("No member threshold satisfies zero public-reference errors")
    if not_member_candidates.empty:
        raise ValueError("No not-member threshold satisfies positive-safety constraint")

    return {
        "member_threshold": float(member_candidates.iloc[0]["threshold"]),
        "not_member_threshold": float(not_member_candidates.iloc[0]["threshold"]),
    }


def cost_sensitivity(
    df: pd.DataFrame,
    profiles: dict[str, dict[str, float]],
    thresholds: Iterable[float] = DEFAULT_THRESHOLDS,
    label_column: str = "is_member",
) -> pd.DataFrame:
    required = {label_column, "semantic_decision", "semantic_confidence"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    threshold_values = tuple(float(v) for v in thresholds)
    rows: list[dict] = []

    for profile_name, profile in profiles.items():
        wrong_member_cost = float(profile["wrong_member_cost"])
        wrong_not_member_cost = float(profile["wrong_not_member_cost"])
        review_cost = float(profile["review_cost"])

        for member_threshold in threshold_values:
            for not_member_threshold in threshold_values:
                routed = route_asymmetric(
                    df,
                    member_threshold=member_threshold,
                    not_member_threshold=not_member_threshold,
                )
                auto_member = routed["route"].eq("AUTO_MEMBER")
                auto_not_member = routed["route"].eq("AUTO_NOT_MEMBER")
                review = routed["route"].eq("HUMAN_REVIEW")
                labels = routed[label_column].astype(int)

                wrong_member = int((auto_member & labels.eq(0)).sum())
                wrong_not_member = int((auto_not_member & labels.eq(1)).sum())
                review_rows = int(review.sum())

                normalized_cost = (
                    wrong_member * wrong_member_cost
                    + wrong_not_member * wrong_not_member_cost
                    + review_rows * review_cost
                )

                rows.append(
                    {
                        "profile": profile_name,
                        "wrong_member_cost": wrong_member_cost,
                        "wrong_not_member_cost": wrong_not_member_cost,
                        "review_cost": review_cost,
                        "member_threshold": member_threshold,
                        "not_member_threshold": not_member_threshold,
                        "auto_rows": int((auto_member | auto_not_member).sum()),
                        "review_rows": review_rows,
                        "wrong_member": wrong_member,
                        "wrong_not_member": wrong_not_member,
                        "normalized_cost": normalized_cost,
                    }
                )

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["profile", "normalized_cost", "review_rows"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
