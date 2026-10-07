from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"


def summarize(df: pd.DataFrame) -> dict:
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "null_fraction": {
            column: round(float(df[column].isna().mean()), 4)
            for column in df.columns
        },
        "duplicate_rows": int(df.duplicated().sum()),
    }


def main() -> None:
    london_path = RAW_DIR / "London.csv"
    annotated_path = RAW_DIR / "London_annotated.csv"

    missing = [str(p) for p in [london_path, annotated_path] if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing dataset files. Run `python -m src.data.download_london` first. "
            f"Missing: {missing}"
        )

    london = pd.read_csv(london_path)
    annotated = pd.read_csv(annotated_path)

    report = {
        "London.csv": summarize(london),
        "London_annotated.csv": summarize(annotated),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("\nLondon.csv sample:")
    print(london.head(3).to_string(index=False))
    print("\nLondon_annotated.csv sample:")
    print(annotated.head(3).to_string(index=False))


if __name__ == "__main__":
    main()
