from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.scoring.quality_impact import build_quality_impact_scores, summarize_quality_impact

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCATION = ROOT / "reports" / "location" / "semantic" / "location_gated_results.csv"
DEFAULT_CATEGORY = ROOT / "reports" / "impact" / "category_overlap_evidence.csv"
DEFAULT_OUTPUT = ROOT / "reports" / "impact" / "quality_impact_scores.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "impact" / "quality_impact_summary.json"


def main(location_path: Path, category_path: Path, output_path: Path, summary_path: Path) -> None:
    location = pd.read_csv(location_path)
    category = pd.read_csv(category_path)
    scores = build_quality_impact_scores(location, category)
    summary = summarize_quality_impact(scores)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(scores.head(20).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build unified category + location quality impact scores.")
    parser.add_argument("--location", type=Path, default=DEFAULT_LOCATION)
    parser.add_argument("--category", type=Path, default=DEFAULT_CATEGORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    main(args.location, args.category, args.output, args.summary)
