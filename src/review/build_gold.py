from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.review.adjudication import merge_adjudications
from src.review.gold import build_adjudicated_gold, build_regression_set


def main(
    queue_path: Path,
    adjudications_path: Path,
    gold_path: Path,
    regression_path: Path,
) -> None:
    if not queue_path.exists():
        raise FileNotFoundError(f"Missing review queue: {queue_path}")
    if not adjudications_path.exists():
        raise FileNotFoundError(f"Missing adjudications: {adjudications_path}")

    queue = pd.read_csv(queue_path)
    adjudications = pd.read_csv(adjudications_path)
    reviewed = merge_adjudications(queue, adjudications)
    gold = build_adjudicated_gold(reviewed)
    regression = build_regression_set(reviewed)

    gold_path.parent.mkdir(parents=True, exist_ok=True)
    gold.to_csv(gold_path, index=False)
    regression.to_csv(regression_path, index=False)

    print(f"adjudicated cases: {len(gold)}")
    print(f"regression cases: {len(regression)}")
    print(f"saved: {gold_path}")
    print(f"saved: {regression_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build adjudicated gold and regression cases."
    )
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--regression", type=Path, required=True)
    args = parser.parse_args()
    main(args.queue, args.adjudications, args.gold, args.regression)
