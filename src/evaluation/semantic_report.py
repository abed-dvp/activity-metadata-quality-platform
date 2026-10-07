from __future__ import annotations

from typing import Any

import pandas as pd

from src.evaluation.metrics import binary_metrics


def evaluate_semantic_sample(df: pd.DataFrame) -> dict[str, Any]:
    required = {"is_member", "prediction", "semantic_decision"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    baseline = binary_metrics(
        df["is_member"].astype(int).tolist(),
        df["prediction"].astype(int).tolist(),
    )

    decided = df.loc[df["semantic_decision"] != "uncertain"].copy()
    decided["semantic_prediction"] = decided["semantic_decision"].map(
        {"member": 1, "not_member": 0}
    ).astype(int)

    decided_metrics = binary_metrics(
        decided["is_member"].astype(int).tolist(),
        decided["semantic_prediction"].astype(int).tolist(),
    ) if len(decided) else binary_metrics([], [])

    conservative = df["semantic_decision"].map(
        {"member": 1, "not_member": 0, "uncertain": 0}
    ).astype(int)
    conservative_metrics = binary_metrics(
        df["is_member"].astype(int).tolist(), conservative.tolist()
    )

    return {
        "rows": int(len(df)),
        "decided_rows": int(len(decided)),
        "coverage": float(len(decided) / len(df)) if len(df) else 0.0,
        "abstention_rate": float((df["semantic_decision"] == "uncertain").mean()) if len(df) else 0.0,
        "baseline": baseline.to_dict(),
        "semantic_decided_only": decided_metrics.to_dict(),
        "semantic_conservative": conservative_metrics.to_dict(),
    }
