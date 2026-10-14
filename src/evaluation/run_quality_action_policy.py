from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.policy.quality_action_policy import apply_action_policy, summarize_action_policy

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "reports" / "impact" / "quality_impact_scores.csv"
DEFAULT_OUTPUT = ROOT / "reports" / "impact" / "quality_action_queue.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "impact" / "quality_action_summary.json"


def main(input_path: Path, output_path: Path, summary_path: Path) -> None:
    scores = pd.read_csv(input_path)
    actions = apply_action_policy(scores)
    summary = summarize_action_policy(actions)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    actions.to_csv(output_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(actions.head(20).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply the unified quality action policy.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    main(args.input, args.output, args.summary)
