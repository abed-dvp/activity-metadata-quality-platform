from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.prepare_category_ground_truth import normalize_columns, detect_identity_columns

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


def build_evaluation_dataset(catalog: pd.DataFrame, annotated: pd.DataFrame) -> pd.DataFrame:
    labels = normalize_columns(annotated)
    name_col, address_col = detect_identity_columns(labels)
    category_cols = [c for c in labels.columns if c not in {name_col, address_col}]

    for category in category_cols:
        labels[category] = pd.to_numeric(labels[category], errors="coerce").fillna(0).astype(int)

    catalog = catalog.copy()
    catalog["_name_key"] = _key(catalog["name"])
    catalog["_address_key"] = _key(catalog["address"])
    labels["_name_key"] = _key(labels[name_col])
    labels["_address_key"] = _key(labels[address_col])

    merged = catalog.merge(
        labels[["_name_key", "_address_key", *category_cols]],
        on=["_name_key", "_address_key"],
        how="inner",
        validate="one_to_one",
    )

    long = merged.melt(
        id_vars=[
            "entity_id",
            "name",
            "address",
            "source_category",
            "details",
            "review_text",
        ],
        value_vars=category_cols,
        var_name="category",
        value_name="is_member",
    )

    long["is_member"] = long["is_member"].astype(int)
    long["label_source"] = "human_annotation"
    long["evaluation_dataset_version"] = "london_category_eval_v1"
    return long.drop(columns=[], errors="ignore")


def main(catalog_path: Path, annotations_path: Path, output_path: Path) -> None:
    if not catalog_path.exists():
        raise FileNotFoundError(f"Missing canonical catalog: {catalog_path}")
    if not annotations_path.exists():
        raise FileNotFoundError(f"Missing annotations: {annotations_path}")

    out = build_evaluation_dataset(
        pd.read_csv(catalog_path),
        pd.read_csv(annotations_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)

    print(f"evaluation rows: {len(out):,}")
    print(f"entities: {out['entity_id'].nunique():,}")
    print(f"categories: {out['category'].nunique():,}")
    print(f"positive labels: {int(out['is_member'].sum()):,}")
    print(f"saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build an evaluation-ready category table.")
    parser.add_argument("--catalog", type=Path, default=PROCESSED_DIR / "catalog.csv")
    parser.add_argument("--annotations", type=Path, default=RAW_DIR / "London_annotated.csv")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "category_evaluation.csv")
    args = parser.parse_args()
    main(args.catalog, args.annotations, args.output)
