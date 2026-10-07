from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from src.evaluation.asymmetric_routing import (
    cost_sensitivity,
    lane_threshold_validation,
    select_safety_constrained_thresholds,
)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "phase6"
DEFAULT_COSTS = ROOT / "config" / "routing_cost_scenarios.yml"


def load_overrides(path: Path) -> dict[str, int]:
    df = pd.read_csv(path)
    accepted = df.loc[df["candidate_label"].notna()].copy()
    return {
        str(row["entity_id"]): int(row["candidate_label"])
        for _, row in accepted.iterrows()
    }


def load_profiles(path: Path) -> dict[str, dict[str, float]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload["profiles"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 6 lane-specific threshold and cost validation."
    )
    parser.add_argument("--representative", type=Path, required=True)
    parser.add_argument("--positive-diagnostic", type=Path, required=True)
    parser.add_argument("--adjudication-overrides", type=Path, required=True)
    parser.add_argument("--cost-config", type=Path, default=DEFAULT_COSTS)
    args = parser.parse_args()

    representative = pd.read_csv(args.representative)
    positive = pd.read_csv(args.positive_diagnostic)
    overrides = load_overrides(args.adjudication_overrides)
    profiles = load_profiles(args.cost_config)

    validation = lane_threshold_validation(
        representative,
        positive,
        assisted_overrides=overrides,
    )
    safe = select_safety_constrained_thresholds(validation)

    union = pd.concat([representative, positive], ignore_index=True)
    union = union.drop_duplicates("entity_id", keep="first")
    costs = cost_sensitivity(union, profiles)

    REPORTS.mkdir(parents=True, exist_ok=True)
    validation.to_csv(REPORTS / "lane_threshold_validation.csv", index=False)
    costs.to_csv(REPORTS / "cost_sensitivity_grid.csv", index=False)

    best_cost = (
        costs.groupby("profile", as_index=False)
        .first()
        .sort_values("profile")
    )
    best_cost.to_csv(REPORTS / "cost_sensitivity_best.csv", index=False)

    summary = {
        "phase": "phase6_asymmetric_routing",
        "safety_constrained_candidate": safe,
        "production_enabled": False,
        "cost_units": "normalized_sensitivity_units_not_currency",
        "governance_note": (
            "Cost-only optimization is subordinate to safety constraints. "
            "Public-label-positive sensitivity cases must not be auto-rejected."
        ),
    }
    (REPORTS / "phase6_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    print(validation.to_string(index=False))
    print(best_cost.to_string(index=False))


if __name__ == "__main__":
    main()
