import pandas as pd

from src.review.build_location_review_queue import build_review_queue, summarize


def test_review_queue_uses_address_gate_before_pin_mismatch():
    results = pd.DataFrame(
        [
            {
                "entity_id": "acorn",
                "name": "Acorn 20/20",
                "address": "20 Richmond Rd",
                "latitude": 51.413,
                "longitude": -0.3005,
                "geocoder_status": "resolved",
                "reference_latitude": 51.5656,
                "reference_longitude": 0.0013,
                "reference_display_name": "20 Richmond Road, Leytonstone, London",
                "distance_m": 26915.4,
                "consistency_decision": "suspicious",
            },
            {
                "entity_id": "city-only",
                "name": "Italian Gardens",
                "address": "London, United Kingdom",
                "latitude": 51.51,
                "longitude": -0.17,
                "geocoder_status": "resolved",
                "reference_latitude": 51.507,
                "reference_longitude": -0.127,
                "reference_display_name": "Greater London",
                "distance_m": 3337.6,
                "consistency_decision": "suspicious",
            },
        ]
    )

    queue = build_review_queue(results)

    acorn = queue.loc[queue["entity_id"] == "acorn"].iloc[0]
    city = queue.loc[queue["entity_id"] == "city-only"].iloc[0]

    assert acorn["quality_gate_route"] == "ADDRESS_OR_GEOCODER_REVIEW"
    assert acorn["likely_root_cause"] == "address_or_geocoder_mismatch"
    assert city["quality_gate_route"] == "ADDRESS_QUALITY_REVIEW"
    assert city["likely_root_cause"] == "underspecified_address"

    summary = summarize(queue)
    assert summary["coordinate_mismatch_candidates"] == 0
    assert summary["address_or_geocoder_review"] == 1
    assert summary["automatic_correction_enabled"] is False
