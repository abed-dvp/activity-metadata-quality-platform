from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class GeoBounds:
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

    def contains(self, latitude: pd.Series, longitude: pd.Series) -> pd.Series:
        return latitude.between(self.min_latitude, self.max_latitude) & longitude.between(
            self.min_longitude, self.max_longitude
        )


# Deliberately broad plausibility envelope. This is a source-specific diagnostic,
# not a production geofence for bookable activities.
LONDON_PLAUSIBILITY_BOUNDS = GeoBounds(
    min_latitude=51.20,
    max_latitude=51.80,
    min_longitude=-0.70,
    max_longitude=0.40,
)


def _valid_entity_mask(series: pd.Series) -> pd.Series:
    values = series.astype("string")
    return values.notna() & values.str.strip().ne("")


def _eligible_catalog(catalog: pd.DataFrame) -> pd.DataFrame:
    return catalog.loc[_valid_entity_mask(catalog["entity_id"])].copy()


def _finding(
    entity_id: object,
    defect_type: str,
    field_name: str,
    severity: str,
    evidence: str,
) -> dict:
    return {
        "entity_id": str(entity_id),
        "quality_domain": "location",
        "defect_type": defect_type,
        "field_name": field_name,
        "severity": severity,
        "evidence": evidence,
    }


def validate_location_quality(
    catalog: pd.DataFrame,
    bounds: GeoBounds = LONDON_PLAUSIBILITY_BOUNDS,
) -> pd.DataFrame:
    """Return deterministic location findings for rows with valid entity identity.

    Identity-invalid rows belong to the schema-quality domain and are deliberately
    excluded here so one source defect is not double-counted as a location defect.
    """
    required = {"entity_id", "latitude", "longitude"}
    missing_columns = required - set(catalog.columns)
    if missing_columns:
        raise ValueError(f"Missing required location columns: {sorted(missing_columns)}")

    df = _eligible_catalog(catalog)
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")

    findings: list[dict] = []

    both_missing = lat.isna() & lon.isna()
    for idx in df.index[both_missing]:
        findings.append(
            _finding(
                df.at[idx, "entity_id"],
                "MISSING_COORDINATES",
                "latitude,longitude",
                "medium",
                "Both latitude and longitude are missing.",
            )
        )

    partial = lat.isna() ^ lon.isna()
    for idx in df.index[partial]:
        findings.append(
            _finding(
                df.at[idx, "entity_id"],
                "PARTIAL_COORDINATE_PAIR",
                "latitude,longitude",
                "high",
                f"latitude={lat.at[idx]!r}; longitude={lon.at[idx]!r}",
            )
        )

    invalid_lat = lat.notna() & ~lat.between(-90, 90)
    for idx in df.index[invalid_lat]:
        findings.append(
            _finding(
                df.at[idx, "entity_id"],
                "INVALID_LATITUDE",
                "latitude",
                "high",
                f"latitude={lat.at[idx]}",
            )
        )

    invalid_lon = lon.notna() & ~lon.between(-180, 180)
    for idx in df.index[invalid_lon]:
        findings.append(
            _finding(
                df.at[idx, "entity_id"],
                "INVALID_LONGITUDE",
                "longitude",
                "high",
                f"longitude={lon.at[idx]}",
            )
        )

    valid_pair = lat.notna() & lon.notna() & lat.between(-90, 90) & lon.between(-180, 180)

    null_island = valid_pair & lat.abs().lt(0.01) & lon.abs().lt(0.01)
    for idx in df.index[null_island]:
        findings.append(
            _finding(
                df.at[idx, "entity_id"],
                "NULL_ISLAND_COORDINATES",
                "latitude,longitude",
                "high",
                f"latitude={lat.at[idx]}; longitude={lon.at[idx]}",
            )
        )

    outside = valid_pair & ~null_island & ~bounds.contains(lat, lon)
    for idx in df.index[outside]:
        findings.append(
            _finding(
                df.at[idx, "entity_id"],
                "OUTSIDE_LONDON_PLAUSIBILITY_BOUNDS",
                "latitude,longitude",
                "medium",
                f"latitude={lat.at[idx]}; longitude={lon.at[idx]}",
            )
        )

    columns = [
        "entity_id",
        "quality_domain",
        "defect_type",
        "field_name",
        "severity",
        "evidence",
    ]
    return pd.DataFrame(findings, columns=columns)


def summarize_location_quality(catalog: pd.DataFrame, findings: pd.DataFrame) -> dict:
    rows = int(len(catalog))
    eligible = _eligible_catalog(catalog)
    eligible_rows = int(len(eligible))
    excluded_invalid_identity_rows = rows - eligible_rows

    entities_with_findings = int(findings["entity_id"].nunique()) if len(findings) else 0
    lat = pd.to_numeric(eligible["latitude"], errors="coerce")
    lon = pd.to_numeric(eligible["longitude"], errors="coerce")
    complete_pairs = int((lat.notna() & lon.notna()).sum())

    return {
        "catalog_rows": rows,
        "location_eligible_rows": eligible_rows,
        "excluded_invalid_identity_rows": excluded_invalid_identity_rows,
        "complete_coordinate_pairs": complete_pairs,
        "coordinate_pair_coverage": complete_pairs / eligible_rows if eligible_rows else 0.0,
        "entities_with_location_findings": entities_with_findings,
        "entity_finding_rate": entities_with_findings / eligible_rows if eligible_rows else 0.0,
        "findings": int(len(findings)),
        "findings_by_defect_type": (
            findings["defect_type"].value_counts().sort_index().to_dict()
            if len(findings)
            else {}
        ),
        "findings_by_severity": (
            findings["severity"].value_counts().sort_index().to_dict()
            if len(findings)
            else {}
        ),
        "production_routing_enabled": False,
        "interpretation": (
            "Deterministic London-specific plausibility baseline on identity-valid entities only. "
            "Address-to-coordinate semantic consistency is not yet validated."
        ),
    }
