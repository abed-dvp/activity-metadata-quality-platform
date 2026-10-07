from __future__ import annotations

import pandas as pd


REQUIRED_FIELDS = ("entity_id", "name", "address")


def validate_catalog(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per deterministic data-quality finding."""
    findings: list[dict] = []

    for field in REQUIRED_FIELDS:
        missing = df[field].isna() | df[field].astype("string").str.strip().eq("")
        for entity_id in df.loc[missing, "entity_id"].astype("string"):
            findings.append(
                {
                    "entity_id": entity_id,
                    "quality_domain": "schema",
                    "defect_type": "REQUIRED_FIELD_MISSING",
                    "field_name": field,
                    "severity": "high",
                }
            )

    duplicate_mask = df["entity_id"].duplicated(keep=False)
    for entity_id in df.loc[duplicate_mask, "entity_id"].astype("string").unique():
        findings.append(
            {
                "entity_id": entity_id,
                "quality_domain": "schema",
                "defect_type": "DUPLICATE_ENTITY_ID",
                "field_name": "entity_id",
                "severity": "high",
            }
        )

    if "latitude" in df.columns:
        invalid_lat = df["latitude"].notna() & ~df["latitude"].between(-90, 90)
        for entity_id in df.loc[invalid_lat, "entity_id"].astype("string"):
            findings.append(
                {
                    "entity_id": entity_id,
                    "quality_domain": "location",
                    "defect_type": "INVALID_LATITUDE",
                    "field_name": "latitude",
                    "severity": "high",
                }
            )

    if "longitude" in df.columns:
        invalid_lon = df["longitude"].notna() & ~df["longitude"].between(-180, 180)
        for entity_id in df.loc[invalid_lon, "entity_id"].astype("string"):
            findings.append(
                {
                    "entity_id": entity_id,
                    "quality_domain": "location",
                    "defect_type": "INVALID_LONGITUDE",
                    "field_name": "longitude",
                    "severity": "high",
                }
            )

    columns = ["entity_id", "quality_domain", "defect_type", "field_name", "severity"]
    return pd.DataFrame(findings, columns=columns)
