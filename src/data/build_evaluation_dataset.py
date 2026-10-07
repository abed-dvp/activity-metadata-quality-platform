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


def _deduplicate_catalog(catalog: pd.DataFrame) -> pd.DataFrame:
    out = catalog.copy()
    out["_name_key"] = _key(out["name"])
    out["_address_key"] = _key(out["address"])

    valid_identity = (
        out["entity_id"].notna()
        & out["_name_key"].ne("")
        & out["_address_key"].ne("")
    )
    out = out.loc[valid_identity].copy()

    return (
        out.sort_values("entity_id")
        .drop_duplicates(["_name_key", "_address_key"], keep="first")
        .reset_index(drop=True)
    )


def _aggregate_annotations(labels: pd.DataFrame, name_col: str, address_col: str, category_cols: list[str]) -> pd.DataFrame:
    out = labels.copy()
    out["_name_key"] = _key(out[name_col])
    out["_address_key"] = _key(out[address_col])

    for category in category_cols:
        out[category] = pd.to_numeric(out[category], errors="coerce").fillna(0).astype(int)

    valid_identity = out["_name_key"].ne("") & out["_address_key"].ne("")
    out = out.loc[valid_identity].copy()

    return (
        out.groupby(["_name_key", "_address_key"], as_index=False)[category_cols]
        .max()
    )


def build_evaluation_dataset(catalog: pd.DataFrame, annotated: pd.DataFrame) -> pd.DataFrame:
    labels = normalize_columns(annotated)
    name_col, address_col = detect_identity_columns(labels)
    category_cols = [c for c in labels.columns if c not in {name_col, address_col}]

    catalog_unique = _deduplicate_catalog(catalog)
    labels_unique = _aggregate_annotations(labels, name_col, address_col, category_cols)

    merged = catalog_unique.merge(
        labels_unique,
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
    return long


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
