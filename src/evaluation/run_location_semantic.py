from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = (
    "activity-metadata-quality-platform/0.1 "
    "(https://github.com/abed-dvp/activity-metadata-quality-platform)"
)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def deterministic_sample(catalog: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    required = ["entity_id", "name", "address", "latitude", "longitude"]
    missing = [c for c in required if c not in catalog.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    eligible = catalog.copy()
    for col in ("entity_id", "name", "address"):
        eligible = eligible[
            eligible[col].astype("string").notna()
            & eligible[col].astype("string").str.strip().ne("")
        ]
    eligible["latitude"] = pd.to_numeric(eligible["latitude"], errors="coerce")
    eligible["longitude"] = pd.to_numeric(eligible["longitude"], errors="coerce")
    eligible = eligible.dropna(subset=["latitude", "longitude"])

    if len(eligible) < sample_size:
        raise ValueError(f"Only {len(eligible)} eligible rows for sample_size={sample_size}")

    return eligible.sample(n=sample_size, random_state=seed).sort_values("entity_id").reset_index(drop=True)


def geocode_address(address: str, session: requests.Session) -> dict | None:
    query = address
    if "london" not in query.lower():
        query = f"{query}, London, United Kingdom"

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
    }
    response = session.get(
        f"{NOMINATIM_URL}?{urlencode(params)}",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload:
        return None

    best = payload[0]
    return {
        "reference_latitude": float(best["lat"]),
        "reference_longitude": float(best["lon"]),
        "reference_display_name": best.get("display_name", ""),
        "reference_type": best.get("type", ""),
        "reference_osm_type": best.get("osm_type", ""),
        "reference_osm_id": best.get("osm_id"),
    }


def classify_distance(distance_m: float | None) -> str:
    if distance_m is None or pd.isna(distance_m):
        return "unresolved"
    if distance_m <= 500:
        return "consistent"
    if distance_m <= 1500:
        return "uncertain"
    return "suspicious"


def evaluate_sample(sample: pd.DataFrame, delay_seconds: float = 1.1) -> pd.DataFrame:
    rows: list[dict] = []
    session = requests.Session()

    for i, row in sample.iterrows():
        result = geocode_address(str(row["address"]), session)
        if result is None:
            rows.append(
                {
                    **row.to_dict(),
                    "geocoder_status": "unresolved",
                    "reference_latitude": pd.NA,
                    "reference_longitude": pd.NA,
                    "reference_display_name": "",
                    "reference_type": "",
                    "reference_osm_type": "",
                    "reference_osm_id": pd.NA,
                    "distance_m": pd.NA,
                    "consistency_decision": "unresolved",
                }
            )
        else:
            distance = haversine_m(
                float(row["latitude"]),
                float(row["longitude"]),
                result["reference_latitude"],
                result["reference_longitude"],
            )
            rows.append(
                {
                    **row.to_dict(),
                    "geocoder_status": "resolved",
                    **result,
                    "distance_m": round(distance, 1),
                    "consistency_decision": classify_distance(distance),
                }
            )

        if i < len(sample) - 1:
            time.sleep(delay_seconds)

    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame, sample_size: int, seed: int) -> dict:
    resolved = results["geocoder_status"].eq("resolved")
    distances = pd.to_numeric(results["distance_m"], errors="coerce")
    decisions = results["consistency_decision"].value_counts().sort_index().to_dict()

    resolved_distances = distances[resolved & distances.notna()]
    return {
        "phase": "location_address_coordinate_consistency",
        "sample_size": sample_size,
        "seed": seed,
        "resolved_rows": int(resolved.sum()),
        "resolution_rate": float(resolved.mean()) if len(results) else 0.0,
        "decision_counts": {str(k): int(v) for k, v in decisions.items()},
        "median_distance_m": (
            round(float(resolved_distances.median()), 1) if len(resolved_distances) else None
        ),
        "p90_distance_m": (
            round(float(resolved_distances.quantile(0.90)), 1) if len(resolved_distances) else None
        ),
        "max_distance_m": (
            round(float(resolved_distances.max()), 1) if len(resolved_distances) else None
        ),
        "thresholds_m": {
            "consistent_max": 500,
            "uncertain_max": 1500,
            "suspicious_min_exclusive": 1500,
        },
        "reference_provider": "OpenStreetMap Nominatim public API",
        "provider_usage_mode": "one-time small diagnostic sample; single-thread; >=1.1s between requests",
        "production_routing_enabled": False,
        "interpretation": (
            "External geocoding is diagnostic evidence only. Distance can reflect address "
            "centroids, entrance choice, or geocoder ambiguity, so suspicious cases require review."
        ),
    }


def main(
    catalog_path: Path,
    results_path: Path,
    summary_path: Path,
    sample_size: int,
    seed: int,
) -> None:
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"Missing {catalog_path}. Run python -m src.data.run_phase1 first."
        )

    catalog = pd.read_csv(catalog_path)
    sample = deterministic_sample(catalog, sample_size=sample_size, seed=seed)
    results = evaluate_sample(sample)
    summary = summarize(results, sample_size=sample_size, seed=seed)

    results_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(results_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"results: {results_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate address-coordinate consistency on a small geocoded sample.")
    parser.add_argument("--catalog", type=Path, default=PROCESSED / "catalog.csv")
    parser.add_argument("--results", type=Path, default=PROCESSED / "location_semantic_results.csv")
    parser.add_argument("--summary", type=Path, default=PROCESSED / "location_semantic_summary.json")
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261008)
    args = parser.parse_args()
    main(args.catalog, args.results, args.summary, args.sample_size, args.seed)
