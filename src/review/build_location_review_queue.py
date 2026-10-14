from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.quality.address_gate import route_location_quality

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "reports" / "location" / "semantic" / "location_semantic_results.csv"
DEFAULT_QUEUE = ROOT / "reports" / "location" / "semantic" / "location_review_queue.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "location" / "semantic" / "location_review_summary.json"


ROOT_CAUSE_BY_ROUTE = {
    "ADDRESS_OR_GEOCODER_REVIEW": "address_or_geocoder_mismatch",
    "ADDRESS_QUALITY_REVIEW": "underspecified_address",
    "GEOCODER_UNRESOLVED_REVIEW": "geocoder_unresolved",
    "BOUNDARY_REVIEW": "boundary_or_geocoder_ambiguity",
    "COORDINATE_MISMATCH_CANDIDATE": "coordinate_mismatch_candidate",
    "HUMAN_REVIEW": "unknown",
}


def build_review_queue(results: pd.DataFrame) -> pd.DataFrame:
    queue = results.loc[
        results["consistency_decision"].isin(["suspicious", "uncertain", "unresolved"])
    ].copy()

    gate = queue.apply(lambda row: pd.Series(route_location_quality(row)), axis=1)
    queue = pd.concat([queue.reset_index(drop=True), gate.reset_index(drop=True)], axis=1)
    queue["likely_root_cause"] = queue["quality_gate_route"].map(ROOT_CAUSE_BY_ROUTE).fillna("unknown")

    keep = [
        "review_priority",
        "entity_id",
        "name",
        "address",
        "latitude",
        "longitude",
        "geocoder_status",
        "reference_latitude",
        "reference_longitude",
        "reference_display_name",
        "distance_m",
        "consistency_decision",
        "address_specificity",
        "entity_name_match_score",
        "quality_gate_route",
        "likely_bad_field",
        "likely_root_cause",
        "automatic_coordinate_overwrite",
    ]
    return queue[keep].sort_values(
        ["review_priority", "distance_m"],
        ascending=[True, False],
        na_position="last",
    ).reset_index(drop=True)


def summarize(queue: pd.DataFrame) -> dict:
    return {
        "review_rows": int(len(queue)),
        "by_decision": {
            str(k): int(v)
            for k, v in queue["consistency_decision"].value_counts().sort_index().to_dict().items()
        },
        "by_gate_route": {
            str(k): int(v)
            for k, v in queue["quality_gate_route"].value_counts().sort_index().to_dict().items()
        },
        "by_root_cause": {
            str(k): int(v)
            for k, v in queue["likely_root_cause"].value_counts().sort_index().to_dict().items()
        },
        "coordinate_mismatch_candidates": int(
            (queue["quality_gate_route"] == "COORDINATE_MISMATCH_CANDIDATE").sum()
        ),
        "address_or_geocoder_review": int(
            (queue["quality_gate_route"] == "ADDRESS_OR_GEOCODER_REVIEW").sum()
        ),
        "automatic_correction_enabled": False,
        "decision": (
            "Review routing now uses the address/entity quality gate. Large distance alone "
            "cannot create a bad-pin candidate, and no coordinate is automatically overwritten."
        ),
    }


def main(input_path: Path, queue_path: Path, summary_path: Path) -> None:
    results = pd.read_csv(input_path)
    queue = build_review_queue(results)
    summary = summarize(queue)

    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(queue_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(queue.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build gated prioritized location review queue.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    main(args.input, args.queue, args.summary)
