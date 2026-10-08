from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

LONDON_ENVELOPE = {
    "min_lat": 51.20,
    "max_lat": 51.75,
    "min_lon": -0.60,
    "max_lon": 0.40,
}


@dataclass(frozen=True)
class LocationFinding:
    entity_id: str
    defect_type: str
    field_name: str
    severity: str
    label_origin: str = "real_source_observation"

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "quality_domain": "location",
            "defect_type": self.defect_type,
            "field_name": self.field_name,
            "severity": self.severity,
            "label_origin": self.label_origin,
        }


def _blank(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype("string").str.strip().eq("")


def evaluate_location_quality(
    df: pd.DataFrame,
    *,
    label_origin: str = "real_source_observation",
) -> pd.DataFrame:
    required = {"entity_id", "address", "latitude", "longitude"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required location columns: {sorted(missing)}")

    findings: list[LocationFinding] = []

    address_missing = _blank(df["address"])
    lat_missing = df["latitude"].isna()
    lon_missing = df["longitude"].isna()

    for entity_id in df.loc[address_missing, "entity_id"].astype(str):
        findings.append(
            LocationFinding(
                entity_id,
                "LOCATION_ADDRESS_MISSING",
                "address",
                "medium",
                label_origin,
            )
        )

    both_missing = lat_missing & lon_missing
    for entity_id in df.loc[both_missing, "entity_id"].astype(str):
        findings.append(
            LocationFinding(
                entity_id,
                "LOCATION_COORDINATES_MISSING",
                "latitude,longitude",
                "medium",
                label_origin,
            )
        )

    incomplete = lat_missing ^ lon_missing
    for entity_id in df.loc[incomplete, "entity_id"].astype(str):
        findings.append(
            LocationFinding(
                entity_id,
                "LOCATION_COORDINATE_PAIR_INCOMPLETE",
                "latitude,longitude",
                "high",
                label_origin,
            )
        )

    both_present = ~(lat_missing | lon_missing)
    valid_range = (
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    )
    outside_london = both_present & valid_range & ~(
        df["latitude"].between(
            LONDON_ENVELOPE["min_lat"],
            LONDON_ENVELOPE["max_lat"],
        )
        & df["longitude"].between(
            LONDON_ENVELOPE["min_lon"],
            LONDON_ENVELOPE["max_lon"],
        )
    )
    for entity_id in df.loc[outside_london, "entity_id"].astype(str):
        findings.append(
            LocationFinding(
                entity_id,
                "COORDINATES_OUTSIDE_LONDON_ENVELOPE",
                "latitude,longitude",
                "high",
                label_origin,
            )
        )

    if {"catalog_city", "meeting_point_city"}.issubset(df.columns):
        catalog_city = df["catalog_city"].astype("string").str.strip().str.casefold()
        meeting_city = df["meeting_point_city"].astype("string").str.strip().str.casefold()
        contradiction = (
            catalog_city.notna()
            & meeting_city.notna()
            & catalog_city.ne("")
            & meeting_city.ne("")
            & catalog_city.ne(meeting_city)
        )
        for entity_id in df.loc[contradiction, "entity_id"].astype(str):
            findings.append(
                LocationFinding(
                    entity_id,
                    "MEETING_POINT_CITY_CONTRADICTION",
                    "meeting_point_city",
                    "high",
                    label_origin,
                )
            )

    columns = [
        "entity_id",
        "quality_domain",
        "defect_type",
        "field_name",
        "severity",
        "label_origin",
    ]
    return pd.DataFrame([f.to_dict() for f in findings], columns=columns)


def summarize_location_findings(findings: pd.DataFrame, total_rows: int) -> dict:
    counts = (
        findings["defect_type"].value_counts().sort_index().to_dict()
        if not findings.empty
        else {}
    )
    unique_entities = int(findings["entity_id"].nunique()) if not findings.empty else 0
    return {
        "rows_evaluated": int(total_rows),
        "entities_with_location_findings": unique_entities,
        "entity_finding_rate": float(unique_entities / total_rows) if total_rows else 0.0,
        "finding_count": int(len(findings)),
        "findings_by_type": {str(k): int(v) for k, v in counts.items()},
        "location_envelope": LONDON_ENVELOPE,
        "important_caveat": (
            "The London envelope is an operational anomaly boundary, not authoritative city-boundary ground truth."
        ),
    }
