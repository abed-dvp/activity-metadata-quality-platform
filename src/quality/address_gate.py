from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

LOW_SPECIFICITY = {"missing", "country_only", "city_only", "low_specificity"}
NAME_STOPWORDS = {
    "the", "and", "of", "at", "in", "ltd", "limited", "club", "studio",
    "museum", "gallery", "park", "fitness", "centre", "center"
}


def address_specificity(address: object) -> str:
    text = str(address or "").strip().lower()
    if not text or text in {"nan", "<na>"}:
        return "missing"
    if text in {"united kingdom", "uk"}:
        return "country_only"
    if text in {"london, united kingdom", "london"}:
        return "city_only"

    has_digit = any(ch.isdigit() for ch in text)
    comma_parts = [p.strip() for p in text.split(",") if p.strip()]
    if has_digit:
        return "street_number"
    if len(comma_parts) >= 2:
        return "street_or_locality"
    return "low_specificity"


def _tokens(value: object, stopwords: Iterable[str] = NAME_STOPWORDS) -> set[str]:
    text = str(value or "").lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    stopword_set = set(stopwords)
    return {
        token
        for token in tokens
        if len(token) > 1 and not token.isdigit() and token not in stopword_set
    }


def entity_name_match_score(name: object, reference_display_name: object) -> float:
    source = _tokens(name)
    reference = _tokens(reference_display_name)
    if not source or not reference:
        return 0.0
    return len(source & reference) / len(source)


def route_location_quality(row: pd.Series | dict) -> dict:
    get = row.get
    decision = str(get("consistency_decision", ""))
    geocoder_status = str(get("geocoder_status", ""))
    specificity = address_specificity(get("address"))
    name_match = entity_name_match_score(
        get("name"),
        get("reference_display_name"),
    )

    if decision == "consistent":
        route = "PASS"
        likely_field = "none"
        priority = 99
    elif geocoder_status == "unresolved" or decision == "unresolved":
        route = "GEOCODER_UNRESOLVED_REVIEW"
        likely_field = "reference_resolution"
        priority = 2
    elif specificity in LOW_SPECIFICITY:
        route = "ADDRESS_QUALITY_REVIEW"
        likely_field = "address"
        priority = 3
    elif decision == "uncertain":
        route = "BOUNDARY_REVIEW"
        likely_field = "address_or_coordinate"
        priority = 4
    elif decision == "suspicious" and name_match < 0.5:
        route = "ADDRESS_OR_GEOCODER_REVIEW"
        likely_field = "address_or_reference_match"
        priority = 1
    elif decision == "suspicious":
        route = "COORDINATE_MISMATCH_CANDIDATE"
        likely_field = "coordinate"
        priority = 1
    else:
        route = "HUMAN_REVIEW"
        likely_field = "unknown"
        priority = 5

    return {
        "address_specificity": specificity,
        "entity_name_match_score": round(name_match, 3),
        "quality_gate_route": route,
        "likely_bad_field": likely_field,
        "review_priority": priority,
        "automatic_coordinate_overwrite": False,
    }
