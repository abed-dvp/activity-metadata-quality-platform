from __future__ import annotations

import pandas as pd


def build_representative_holdout(
    predictions: pd.DataFrame,
    calibration_entity_ids: set[str],
    category: str = "museum",
    representative_size: int = 600,
    seed: int = 20261007,
) -> tuple[pd.DataFrame, dict]:
    source = predictions.loc[predictions["category"] == category].copy()
    source["entity_id"] = source["entity_id"].astype(str)

    residual = source.loc[
        ~source["entity_id"].isin({str(v) for v in calibration_entity_ids})
    ].copy()

    representative_n = min(representative_size, len(residual))
    representative = residual.sample(n=representative_n, random_state=seed).copy()
    representative["in_representative_sample"] = True

    positives = residual.loc[residual["is_member"].astype(int) == 1].copy()
    positives["in_positive_diagnostic"] = True

    union = pd.concat([representative, positives], ignore_index=True)
    union = union.drop_duplicates("entity_id", keep="first").copy()

    rep_ids = set(representative["entity_id"].astype(str))
    pos_ids = set(positives["entity_id"].astype(str))
    union["in_representative_sample"] = union["entity_id"].astype(str).isin(rep_ids)
    union["in_positive_diagnostic"] = union["entity_id"].astype(str).isin(pos_ids)
    union["holdout_source"] = "residual_excluding_phase3_calibration"

    summary = {
        "category": category,
        "source_rows": int(len(source)),
        "calibration_excluded_entities": int(len(calibration_entity_ids)),
        "residual_rows": int(len(residual)),
        "residual_positive_rows": int(positives["is_member"].astype(int).sum()),
        "residual_prevalence": float(residual["is_member"].astype(int).mean()) if len(residual) else 0.0,
        "representative_rows": int(len(representative)),
        "representative_positive_rows": int(representative["is_member"].astype(int).sum()),
        "representative_prevalence": float(representative["is_member"].astype(int).mean()) if len(representative) else 0.0,
        "union_rows_to_evaluate": int(len(union)),
        "positive_diagnostic_rows": int(len(positives)),
        "seed": seed,
    }
    return union.reset_index(drop=True), summary


def representative_view(evaluated: pd.DataFrame) -> pd.DataFrame:
    return evaluated.loc[evaluated["in_representative_sample"].astype(bool)].copy()


def positive_diagnostic_view(evaluated: pd.DataFrame) -> pd.DataFrame:
    return evaluated.loc[evaluated["in_positive_diagnostic"].astype(bool)].copy()
