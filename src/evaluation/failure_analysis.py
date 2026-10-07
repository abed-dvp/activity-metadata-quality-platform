from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"


def extract_failures(df: pd.DataFrame) -> pd.DataFrame:
    required = {"entity_id", "category", "is_member", "prediction"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.loc[df["is_member"].astype(int) != df["prediction"].astype(int)].copy()
    if out.empty:
        out["error_type"] = pd.Series(dtype="string")
    else:
        out["error_type"] = out.apply(
            lambda row: "FALSE_POSITIVE"
            if int(row["prediction"]) == 1
            else "FALSE_NEGATIVE",
            axis=1,
        )

    preferred = [
        "entity_id",
        "name",
        "category",
        "is_member",
        "prediction",
        "error_type",
        "baseline_score",
        "prediction_evidence",
        "source_category",
        "details",
        "review_text",
    ]
    return out[[c for c in preferred if c in out.columns]]


def summarize_failures(failures: pd.DataFrame) -> pd.DataFrame:
    if failures.empty:
        return pd.DataFrame(columns=["category", "error_type", "count"])
    return (
        failures.groupby(["category", "error_type"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "category"], ascending=[False, True])
        .reset_index(drop=True)
    )


def main(input_path: Path, output_path: Path, summary_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Missing predictions file: {input_path}")

    failures = extract_failures(pd.read_csv(input_path))
    summary = summarize_failures(failures)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    failures.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"failures: {len(failures):,}")
    if not summary.empty:
        print(summary.head(20).to_string(index=False))
    print(f"saved: {output_path}")
    print(f"saved: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract false positives and false negatives.")
    parser.add_argument("--input", type=Path, default=PROCESSED_DIR / "category_predictions.csv")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "category_failures.csv")
    parser.add_argument("--summary", type=Path, default=PROCESSED_DIR / "category_failure_summary.csv")
    args = parser.parse_args()
    main(args.input, args.output, args.summary)
