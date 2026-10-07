from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.data.london_schema import normalize_columns
from src.data.prepare_category_ground_truth import detect_identity_columns

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def _key(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(r"[^a-z0-9]+", "", regex=True)
    )


def profile_dataset(catalog_raw: pd.DataFrame, annotated_raw: pd.DataFrame) -> dict:
    catalog = normalize_columns(catalog_raw)
    annotated = normalize_columns(annotated_raw)

    name_col, address_col = detect_identity_columns(annotated)
    category_cols = [c for c in annotated.columns if c not in {name_col, address_col}]

    catalog_name = next((c for c in ("name", "poi_name", "poi") if c in catalog.columns), None)
    catalog_address = next((c for c in ("address", "full_address", "location") if c in catalog.columns), None)
    if catalog_name is None or catalog_address is None:
        raise ValueError("Catalog must contain name and address-like columns")

    left = catalog[[catalog_name, catalog_address]].copy()
    left["_name_key"] = _key(left[catalog_name])
    left["_address_key"] = _key(left[catalog_address])

    right = annotated[[name_col, address_col, *category_cols]].copy()
    right["_name_key"] = _key(right[name_col])
    right["_address_key"] = _key(right[address_col])

    exact_matches = left.merge(
        right[["_name_key", "_address_key"]].drop_duplicates(),
        on=["_name_key", "_address_key"],
        how="inner",
    )

    positives = {}
    for category in category_cols:
        values = pd.to_numeric(right[category], errors="coerce").fillna(0)
        positives[category] = int((values == 1).sum())

    coordinate_stats = {}
    if "latitude" in catalog.columns:
        lat = pd.to_numeric(catalog["latitude"], errors="coerce")
        coordinate_stats["latitude_non_null"] = int(lat.notna().sum())
        coordinate_stats["latitude_invalid"] = int((lat.notna() & ~lat.between(-90, 90)).sum())
    if "longitude" in catalog.columns:
        lon = pd.to_numeric(catalog["longitude"], errors="coerce")
        coordinate_stats["longitude_non_null"] = int(lon.notna().sum())
        coordinate_stats["longitude_invalid"] = int((lon.notna() & ~lon.between(-180, 180)).sum())

    null_rates = {
        col: round(float(catalog[col].isna().mean()), 4)
        for col in catalog.columns
    }

    return {
        "catalog_rows": int(len(catalog)),
        "annotation_rows": int(len(annotated)),
        "catalog_columns": list(catalog.columns),
        "annotation_columns": list(annotated.columns),
        "annotation_category_count": len(category_cols),
        "annotation_categories": category_cols,
        "positive_labels_by_category": positives,
        "catalog_duplicate_name_address": int(
            left.duplicated(["_name_key", "_address_key"], keep=False).sum()
        ),
        "annotation_duplicate_name_address": int(
            right.duplicated(["_name_key", "_address_key"], keep=False).sum()
        ),
        "exact_name_address_matches": int(len(exact_matches)),
        "join_coverage_vs_annotations": round(
            len(exact_matches) / len(annotated), 4
        ) if len(annotated) else 0.0,
        "catalog_null_rates": null_rates,
        **coordinate_stats,
    }


def main(catalog_path: Path, annotations_path: Path, output_path: Path) -> None:
    if not catalog_path.exists():
        raise FileNotFoundError(f"Missing {catalog_path}")
    if not annotations_path.exists():
        raise FileNotFoundError(f"Missing {annotations_path}")

    profile = profile_dataset(
        pd.read_csv(catalog_path),
        pd.read_csv(annotations_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    print(json.dumps(profile, indent=2))
    print(f"saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile the London catalog and human annotations.")
    parser.add_argument("--catalog", type=Path, default=RAW_DIR / "London.csv")
    parser.add_argument("--annotations", type=Path, default=RAW_DIR / "London_annotated.csv")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "london_profile.json")
    args = parser.parse_args()
    main(args.catalog, args.annotations, args.output)
