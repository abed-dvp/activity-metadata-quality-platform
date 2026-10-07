from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.evaluation.metrics import binary_metrics

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"

REQUIRED_COLUMNS = {"entity_id", "category", "is_member", "prediction"}


def evaluate_predictions(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rows: list[dict] = []
    for category, group in df.groupby("category", dropna=False):
        result = binary_metrics(
            group["is_member"].astype(int).tolist(),
            group["prediction"].astype(int).tolist(),
        )
        positives = int(group["is_member"].astype(int).sum())
        predicted_positives = int(group["prediction"].astype(int).sum())
        rows.append(
            {
                "category": category,
                "n": len(group),
                "positives": positives,
                "predicted_positives": predicted_positives,
                "prevalence": positives / len(group) if len(group) else 0.0,
                **result.to_dict(),
            }
        )

    category_report = pd.DataFrame(rows)

    overall = binary_metrics(
        df["is_member"].astype(int).tolist(),
        df["prediction"].astype(int).tolist(),
    )
    overall_row = {
        "category": "__micro_overall__",
        "n": len(df),
        "positives": int(df["is_member"].astype(int).sum()),
        "predicted_positives": int(df["prediction"].astype(int).sum()),
        "prevalence": float(df["is_member"].astype(int).mean()) if len(df) else 0.0,
        **overall.to_dict(),
    }

    macro_row = {
        "category": "__macro_average__",
        "n": len(df),
        "positives": int(df["is_member"].astype(int).sum()),
        "predicted_positives": int(df["prediction"].astype(int).sum()),
        "prevalence": float(category_report["prevalence"].mean()) if len(category_report) else 0.0,
        "true_positive": int(category_report["true_positive"].sum()) if len(category_report) else 0,
        "false_positive": int(category_report["false_positive"].sum()) if len(category_report) else 0,
        "false_negative": int(category_report["false_negative"].sum()) if len(category_report) else 0,
        "true_negative": int(category_report["true_negative"].sum()) if len(category_report) else 0,
        "precision": float(category_report["precision"].mean()) if len(category_report) else 0.0,
        "recall": float(category_report["recall"].mean()) if len(category_report) else 0.0,
        "f1": float(category_report["f1"].mean()) if len(category_report) else 0.0,
    }

    return pd.concat(
        [category_report, pd.DataFrame([overall_row, macro_row])],
        ignore_index=True,
    )


def main(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Missing predictions file: {input_path}")
    report = evaluate_predictions(pd.read_csv(input_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)
    print(report.to_string(index=False))
    print(f"saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate category predictions by category.")
    parser.add_argument("--input", type=Path, default=PROCESSED_DIR / "category_predictions.csv")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "category_metrics.csv")
    args = parser.parse_args()
    main(args.input, args.output)
