from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.quality.address_gate import route_location_quality

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "reports" / "location" / "semantic" / "location_semantic_results.csv"
DEFAULT_OUTPUT = ROOT / "reports" / "location" / "semantic" / "location_gated_results.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "location" / "semantic" / "location_gate_summary.json"


def apply_gate(results: pd.DataFrame) -> pd.DataFrame:
    gate = results.apply(lambda row: pd.Series(route_location_quality(row)), axis=1)
    return pd.concat([results.reset_index(drop=True), gate.reset_index(drop=True)], axis=1)


def summarize(gated: pd.DataFrame) -> dict:
    reviewable = gated[gated["quality_gate_route"] != "PASS"]
    return {
        "rows": int(len(gated)),
        "pass_rows": int((gated["quality_gate_route"] == "PASS").sum()),
        "review_rows": int(len(reviewable)),
        "route_counts": {
            str(k): int(v)
            for k, v in gated["quality_gate_route"].value_counts().sort_index().to_dict().items()
        },
        "coordinate_mismatch_candidates": int(
            (gated["quality_gate_route"] == "COORDINATE_MISMATCH_CANDIDATE").sum()
        ),
        "address_or_geocoder_review": int(
            (gated["quality_gate_route"] == "ADDRESS_OR_GEOCODER_REVIEW").sum()
        ),
        "automatic_coordinate_overwrite_enabled": False,
        "policy": (
            "Large geocoder distance is insufficient to label a bad pin. "
            "Address specificity and entity-match evidence must pass first."
        ),
    }


def main(input_path: Path, output_path: Path, summary_path: Path) -> None:
    results = pd.read_csv(input_path)
    gated = apply_gate(results)
    summary = summarize(gated)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gated.to_csv(output_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply address/entity gates to cached location diagnostics.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    main(args.input, args.output, args.summary)
