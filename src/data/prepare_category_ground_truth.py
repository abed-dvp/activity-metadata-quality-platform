from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in out.columns
    ]
    return out


def detect_identity_columns(df: pd.DataFrame) -> tuple[str, str]:
    name_candidates = [c for c in df.columns if c in {"poi_name", "name", "poi"}]
    address_candidates = [c for c in df.columns if "address" in c]
    if not name_candidates or not address_candidates:
        raise ValueError(
            "Could not identify POI name/address columns in annotated dataset. "
            f"Columns: {list(df.columns)}"
        )
    return name_candidates[0], address_candidates[0]


def main() -> None:
    source = RAW_DIR / "London_annotated.csv"
    if not source.exists():
        raise FileNotFoundError(
            "London_annotated.csv not found. Run `python -m src.data.download_london` first."
        )

    df = normalize_columns(pd.read_csv(source))
    name_col, address_col = detect_identity_columns(df)
    category_cols = [c for c in df.columns if c not in {name_col, address_col}]

    for column in category_cols:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)

    long = df.melt(
        id_vars=[name_col, address_col],
        value_vars=category_cols,
        var_name="category",
        value_name="is_member",
    )
    long = long[long["is_member"] == 1].copy()
    long = long.rename(columns={name_col: "poi_name", address_col: "address"})
    long["label_source"] = "human_annotation"
    long["dataset_version"] = "figshare_27628029_v1"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    target = PROCESSED_DIR / "category_ground_truth.csv"
    long.to_csv(target, index=False)

    print(f"rows: {len(long)}")
    print(f"categories: {long['category'].nunique()}")
    print(f"saved: {target}")


if __name__ == "__main__":
    main()
