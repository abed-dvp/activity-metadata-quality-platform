from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.profile_london import profile_dataset
from src.data.prepare_london_catalog import prepare_catalog
from src.data.build_evaluation_dataset import build_evaluation_dataset
from src.data.io import read_source_csv

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"


def main() -> None:
    london_path = RAW / "London.csv"
    annotated_path = RAW / "London_annotated.csv"
    if not london_path.exists() or not annotated_path.exists():
        raise FileNotFoundError(
            "London.csv and London_annotated.csv must exist under data/raw/. "
            "Run `python -m src.data.download_london` or download the two official files manually."
        )

    raw = read_source_csv(london_path)
    annotated = read_source_csv(annotated_path)

    OUT.mkdir(parents=True, exist_ok=True)

    profile = profile_dataset(raw, annotated)
    pd.Series(profile, dtype="object").to_json(OUT / "london_profile.json", indent=2)

    catalog = prepare_catalog(raw)
    catalog.to_csv(OUT / "catalog.csv", index=False)

    eval_df = build_evaluation_dataset(catalog, annotated)
    eval_df.to_csv(OUT / "category_evaluation.csv", index=False)

    print(f"catalog rows: {len(catalog):,}")
    print(f"evaluation rows: {len(eval_df):,}")
    print(f"categories: {eval_df['category'].nunique():,}")
    print(
        "join coverage vs all annotations: "
        f"{profile['join_coverage_vs_all_annotations']:.1%}"
    )
    print(
        "join coverage vs valid annotations: "
        f"{profile['join_coverage_vs_valid_annotations']:.1%}"
    )
    print(f"outputs: {OUT}")


if __name__ == "__main__":
    main()
