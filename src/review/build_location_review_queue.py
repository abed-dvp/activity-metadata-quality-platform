from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "reports" / "location" / "semantic" / "location_semantic_results.csv"
DEFAULT_QUEUE = ROOT / "reports" / "location" / "semantic" / "location_review_queue.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "location" / "semantic" / "location_review_summary.json"


def address_specificity(address: object) -> str:
    text = str(address or "").strip().lower()
    if not text or text in {"nan", "<na>"}:
        return "missing"
    if text in {"united kingdom", "uk"}:
        return "country_only"
    if text in {"london, united kingdom", "london"}:
        return "city_only"

    has_digit = any(ch.isdigit() for ch in text)
    comma_parts = [p.strip() for p in text.split(",") if p.strip()]
    if has_digit:
        return "street_number"
    if len(comma_parts) >= 2:
        return "street_or_locality"
    return "low_specificity"


def likely_root_cause(row: pd.Series) -> str:
    decision = str(row.get("consistency_decision", ""))
    specificity = address_specificity(row.get("address"))

    if decision == "unresolved":
        return "geocoder_unresolved"
    if specificity in {"missing", "country_only", "city_only", "low_specificity"}:
        return "underspecified_address"
    if decision == "suspicious":
        return "address_coordinate_mismatch_candidate"
    if decision == "uncertain":
        return "boundary_or_geocoder_ambiguity"
    return "no_review"


def priority(row: pd.Series) -> int:
    cause = likely_root_cause(row)
    if cause == "address_coordinate_mismatch_candidate":
        return 1
    if cause == "geocoder_unresolved":
        return 2
    if cause == "underspecified_address":
        return 3
    if cause == "boundary_or_geocoder_ambiguity":
        return 4
    return 99


def build_review_queue(results: pd.DataFrame) -> pd.DataFrame:
    queue = results.loc[
        results["consistency_decision"].isin(["suspicious", "uncertain", "unresolved"])
    ].copy()

    queue["address_specificity"] = queue["address"].map(address_specificity)
    queue["likely_root_cause"] = queue.apply(likely_root_cause, axis=1)
    queue["review_priority"] = queue.apply(priority, axis=1)

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
        "likely_root_cause",
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
        "by_root_cause": {
            str(k): int(v)
            for k, v in queue["likely_root_cause"].value_counts().sort_index().to_dict().items()
        },
        "priority_1_mismatch_candidates": int((queue["review_priority"] == 1).sum()),
        "automatic_correction_enabled": False,
        "decision": (
            "Location anomalies are routed to human review with address specificity separated "
            "from coordinate-mismatch evidence. No coordinate is automatically overwritten."
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
    parser = argparse.ArgumentParser(description="Build prioritized location review queue.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    main(args.input, args.queue, args.summary)
