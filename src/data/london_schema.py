from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class CanonicalField:
    name: str
    candidates: tuple[str, ...]
    required: bool = False


CANONICAL_FIELDS: tuple[CanonicalField, ...] = (
    CanonicalField("source_id", ("id", "poi_id", "place_id"), required=True),
    CanonicalField("name", ("name", "poi_name", "poi"), required=True),
    CanonicalField("source_category", ("category", "type", "poi_category")),
    CanonicalField("address", ("address", "full_address", "location"), required=True),
    CanonicalField("latitude", ("latitude", "lat")),
    CanonicalField("longitude", ("longitude", "lon", "lng")),
    CanonicalField("details", ("details", "description", "description_text")),
    CanonicalField("review_text", ("review_text", "reviews", "review", "all_words")),
)


def normalize_column_name(value: object) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalize_column_name(c) for c in out.columns]
    return out


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    column_set = set(columns)
    return next((candidate for candidate in candidates if candidate in column_set), None)


def resolve_mapping(df: pd.DataFrame) -> dict[str, str | None]:
    normalized = normalize_columns(df)
    mapping: dict[str, str | None] = {}
    missing_required: list[str] = []

    for field in CANONICAL_FIELDS:
        matched = first_existing(normalized.columns, field.candidates)
        mapping[field.name] = matched
        if field.required and matched is None:
            missing_required.append(field.name)

    if missing_required:
        raise ValueError(
            "Missing required canonical fields: "
            f"{missing_required}. Available columns: {list(normalized.columns)}"
        )

    return mapping
