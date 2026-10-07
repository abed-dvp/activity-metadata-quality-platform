from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.london_schema import normalize_columns, resolve_mapping

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .replace({"": pd.NA})
    )


def prepare_catalog(df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_columns(df)
    mapping = resolve_mapping(source)

    out = pd.DataFrame(index=source.index)
    for target, source_col in mapping.items():
        out[target] = source[source_col] if source_col is not None else pd.NA

    out["source_id"] = normalize_text(out["source_id"])
    out["entity_id"] = "london_poi_" + out["source_id"].astype("string")
    out["name"] = normalize_text(out["name"])
    out["address"] = normalize_text(out["address"])
    out["source_category"] = normalize_text(out["source_category"])
    out["details"] = normalize_text(out["details"])
    out["review_text"] = normalize_text(out["review_text"])

    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")

    out["dataset_name"] = "Enriched Tourism Dataset London (POIs)"
    out["dataset_version"] = "mendeley_gw9hjn4v65_v2"
    out["license"] = "CC BY 4.0"

    columns = [
        "entity_id",
        "source_id",
        "name",
        "source_category",
        "address",
        "latitude",
        "longitude",
        "details",
        "review_text",
        "dataset_name",
        "dataset_version",
        "license",
    ]
    return out[columns]


def main(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(
            f"{input_path} does not exist. Run `python -m src.data.download_london` first."
        )

    catalog = prepare_catalog(pd.read_csv(input_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(output_path, index=False)

    print(f"rows: {len(catalog):,}")
    print(f"unique entities: {catalog['entity_id'].nunique():,}")
    print(f"saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize London POIs into the canonical catalog schema.")
    parser.add_argument("--input", type=Path, default=RAW_DIR / "London.csv")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "catalog.csv")
    args = parser.parse_args()
    main(args.input, args.output)
