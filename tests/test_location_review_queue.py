import pandas as pd

from src.review.build_location_review_queue import (
    address_specificity,
    build_review_queue,
    summarize,
)


def test_address_specificity_distinguishes_city_only_from_street_number():
    assert address_specificity("London, United Kingdom") == "city_only"
    assert address_specificity("United Kingdom") == "country_only"
    assert address_specificity("207 Upper St") == "street_number"
    assert address_specificity("Grahame Park Way, London") == "street_or_locality"


def test_review_queue_separates_address_quality_from_pin_mismatch():
    results = pd.DataFrame(
        [
            {
                "entity_id": "a",
                "name": "A",
                "address": "20 Richmond Rd",
                "latitude": 51.4,
                "longitude": -0.3,
                "geocoder_status": "resolved",
                "reference_latitude": 51.56,
                "reference_longitude": 0.0,
                "reference_display_name": "20 Richmond Road",
                "distance_m": 26000,
                "consistency_decision": "suspicious",
            },
            {
                "entity_id": "b",
                "name": "B",
                "address": "London, United Kingdom",
                "latitude": 51.47,
                "longitude": -0.23,
                "geocoder_status": "resolved",
                "reference_latitude": 51.50,
                "reference_longitude": -0.12,
                "reference_display_name": "Greater London",
                "distance_m": 8000,
                "consistency_decision": "suspicious",
            },
        ]
    )
    queue = build_review_queue(results)

    assert queue.loc[queue["entity_id"] == "a", "likely_root_cause"].iloc[0] == "address_coordinate_mismatch_candidate"
    assert queue.loc[queue["entity_id"] == "b", "likely_root_cause"].iloc[0] == "underspecified_address"
    assert summarize(queue)["priority_1_mismatch_candidates"] == 1
