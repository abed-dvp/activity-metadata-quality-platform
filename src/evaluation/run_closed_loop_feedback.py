from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.feedback.closed_loop import (
    build_feedback_learning_events,
    build_regression_cases,
    summarize_closed_loop,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ACTIONS = ROOT / "reports" / "impact" / "quality_action_queue.csv"
DEFAULT_FEEDBACK = ROOT / "reports" / "feedback" / "review_feedback.csv"
DEFAULT_LOCATION = ROOT / "reports" / "location" / "semantic" / "location_gated_results.csv"
DEFAULT_EVENTS = ROOT / "reports" / "feedback" / "learning_events.csv"
DEFAULT_REGRESSION = ROOT / "reports" / "feedback" / "closed_loop_regression_cases.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "feedback" / "closed_loop_summary.json"


def main(
    action_path: Path,
    feedback_path: Path,
    location_path: Path,
    events_path: Path,
    regression_path: Path,
    summary_path: Path,
) -> None:
    actions = pd.read_csv(action_path)
    feedback = pd.read_csv(feedback_path)
    location = pd.read_csv(location_path)

    events = build_feedback_learning_events(actions, feedback)
    regression = build_regression_cases(location, events)
    summary = summarize_closed_loop(actions, events, regression)

    events_path.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(events_path, index=False)
    regression.to_csv(regression_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(events.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run closed-loop review feedback evaluation.")
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--location", type=Path, default=DEFAULT_LOCATION)
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument("--regression", type=Path, default=DEFAULT_REGRESSION)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    main(
        args.actions,
        args.feedback,
        args.location,
        args.events,
        args.regression,
        args.summary,
    )
