from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.baselines.category_keyword import load_config, predict_categories
from src.evaluation.category_report import evaluate_predictions
from src.evaluation.failure_analysis import extract_failures, summarize_failures

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_CONFIG = ROOT / "config" / "category_baseline.yml"


def main(input_path: Path, threshold: float, config_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing {input_path}. Run `python -m src.data.run_phase1` after placing the London files in data/raw/."
        )

    evaluation = pd.read_csv(input_path)
    config = load_config(config_path, threshold=threshold)
    predictions = predict_categories(evaluation, config)
    metrics = evaluate_predictions(predictions)
    failures = extract_failures(predictions)
    failure_summary = summarize_failures(failures)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PROCESSED_DIR / "category_predictions.csv", index=False)
    metrics.to_csv(PROCESSED_DIR / "category_metrics.csv", index=False)
    failures.to_csv(PROCESSED_DIR / "category_failures.csv", index=False)
    failure_summary.to_csv(PROCESSED_DIR / "category_failure_summary.csv", index=False)

    micro = metrics.loc[metrics["category"] == "__micro_overall__"].iloc[0]
    macro = metrics.loc[metrics["category"] == "__macro_average__"].iloc[0]
    summary = {
        "baseline": "deterministic_keyword_v1",
        "threshold": threshold,
        "rows": int(len(predictions)),
        "entities": int(predictions["entity_id"].nunique()),
        "categories": int(predictions["category"].nunique()),
        "gold_positives": int(predictions["is_member"].astype(int).sum()),
        "predicted_positives": int(predictions["prediction"].astype(int).sum()),
        "failures": int(len(failures)),
        "micro_precision": float(micro["precision"]),
        "micro_recall": float(micro["recall"]),
        "micro_f1": float(micro["f1"]),
        "macro_precision": float(macro["precision"]),
        "macro_recall": float(macro["recall"]),
        "macro_f1": float(macro["f1"]),
    }
    (PROCESSED_DIR / "phase2_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    print(f"outputs: {PROCESSED_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 2 deterministic category baseline and evaluation.")
    parser.add_argument("--input", type=Path, default=PROCESSED_DIR / "category_evaluation.csv")
    parser.add_argument("--threshold", type=float, default=2.0)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    main(args.input, args.threshold, args.config)
