from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.evaluation.routing import threshold_sweep
from src.review.queue import build_review_queue, review_queue_summary

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports" / "phase4"


def main(input_path: Path, category: str) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Missing semantic calibration file: {input_path}")

    df = pd.read_csv(input_path)
    df = df.loc[df["category"] == category].copy()

    queue = build_review_queue(df)
    summary = review_queue_summary(queue)
    summary.update({
        "category": category,
        "source_rows": int(len(df)),
        "review_fraction": float(len(queue) / len(df)) if len(df) else 0.0,
        "routing_status": "CALIBRATION_ONLY",
    })
    sweep = threshold_sweep(df)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    queue_path = PROCESSED / f"{category}_review_queue.csv"
    queue.to_csv(queue_path, index=False)

    (REPORTS / "review_queue_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    sweep.to_csv(REPORTS / "routing_threshold_sweep.csv", index=False)

    adjudication_template = PROCESSED / f"{category}_adjudications.csv"
    if not adjudication_template.exists():
        pd.DataFrame(columns=[
            "review_case_id",
            "reviewer_label",
            "reviewer_confidence",
            "resolution_type",
            "reviewer_notes",
            "reviewer_id",
            "reviewed_at",
        ]).to_csv(adjudication_template, index=False)

    print(json.dumps(summary, indent=2))
    print(sweep.to_string(index=False))
    print(f"queue: {queue_path}")
    print(f"adjudications: {adjudication_template}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare Phase 4 review queue and routing analysis."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROCESSED / "semantic_museum_v1_calibration.csv",
    )
    parser.add_argument("--category", default="museum")
    args = parser.parse_args()
    main(args.input, args.category)
