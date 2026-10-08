from __future__ import annotations

import random

import pandas as pd

from src.quality.location import evaluate_location_quality

INJECTION_TYPES = (
    "LOCATION_ADDRESS_MISSING",
    "LOCATION_COORDINATE_PAIR_INCOMPLETE",
    "LOCATION_OUTSIDE_EXPECTED_REGION",
    "LOCATION_WRONG_CITY",
    "MEETING_POINT_CONTRADICTION",
)


def build_controlled_location_benchmark(
    catalog: pd.DataFrame,
    *,
    sample_size: int = 400,
    seed: int = 20261008,
) -> pd.DataFrame:
    real_findings = evaluate_location_quality(catalog)
    bad_ids = set(real_findings["entity_id"].astype(str)) if not real_findings.empty else set()

    clean = catalog.loc[
        ~catalog["entity_id"].astype(str).isin(bad_ids)
    ].copy()
    if clean.empty:
        raise ValueError("No clean rows available for location benchmark")

    n = min(sample_size, len(clean))
    sample = clean.sample(n=n, random_state=seed).reset_index(drop=True).copy()
    sample["catalog_city"] = "London"
    sample["location_city"] = "London"
    sample["meeting_point_city"] = "London"
    sample["label_origin"] = "synthetic_injection"

    rng = random.Random(seed)
    defect_order = [INJECTION_TYPES[i % len(INJECTION_TYPES)] for i in range(n)]
    rng.shuffle(defect_order)
    sample["injected_defect_type"] = defect_order

    for idx, defect in enumerate(defect_order):
        if defect == "LOCATION_ADDRESS_MISSING":
            sample.at[idx, "address"] = pd.NA
        elif defect == "LOCATION_COORDINATE_PAIR_INCOMPLETE":
            sample.at[idx, "longitude"] = pd.NA
        elif defect == "LOCATION_OUTSIDE_EXPECTED_REGION":
            sample.at[idx, "latitude"] = 48.8566
            sample.at[idx, "longitude"] = 2.3522
        elif defect == "LOCATION_WRONG_CITY":
            sample.at[idx, "location_city"] = "Manchester"
        elif defect == "MEETING_POINT_CONTRADICTION":
            sample.at[idx, "meeting_point_city"] = "Paris"

    return sample


def evaluate_controlled_benchmark(benchmark: pd.DataFrame) -> dict:
    findings = evaluate_location_quality(
        benchmark,
        label_origin="synthetic_injection",
    )

    gold = {
        (str(row.entity_id), str(row.injected_defect_type))
        for row in benchmark.itertuples(index=False)
    }
    predicted = {
        (str(row.entity_id), str(row.defect_type))
        for row in findings.itertuples(index=False)
    }

    tp = len(gold & predicted)
    fp = len(predicted - gold)
    fn = len(gold - predicted)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "rows": int(len(benchmark)),
        "label_origin": "synthetic_injection",
        "true_positive_events": tp,
        "false_positive_events": fp,
        "false_negative_events": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "important_caveat": (
            "This benchmark measures detection of explicitly injected structured defects only. "
            "It must never be combined with real-source quality metrics."
        ),
    }
