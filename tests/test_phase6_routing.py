import pandas as pd

from src.evaluation.asymmetric_routing import (
    cost_sensitivity,
    lane_threshold_validation,
    route_asymmetric,
    select_safety_constrained_thresholds,
)


def representative_fixture():
    return pd.DataFrame(
        {
            "entity_id": ["a", "b", "c", "d", "e"],
            "is_member": [1, 0, 0, 0, 1],
            "semantic_decision": [
                "member",
                "member",
                "not_member",
                "not_member",
                "uncertain",
            ],
            "semantic_confidence": [0.99, 0.95, 0.99, 0.85, 0.4],
            "provider_error": [None, None, None, None, None],
        }
    )


def positive_fixture():
    return pd.DataFrame(
        {
            "entity_id": ["a", "e", "f"],
            "is_member": [1, 1, 1],
            "semantic_decision": ["member", "uncertain", "not_member"],
            "semantic_confidence": [0.99, 0.4, 0.95],
        }
    )


def test_asymmetric_router_uses_independent_thresholds():
    routed = route_asymmetric(
        representative_fixture(),
        member_threshold=0.98,
        not_member_threshold=0.80,
    )
    assert list(routed["route"]) == [
        "AUTO_MEMBER",
        "HUMAN_REVIEW",
        "AUTO_NOT_MEMBER",
        "AUTO_NOT_MEMBER",
        "HUMAN_REVIEW",
    ]


def test_provider_error_always_routes_to_review():
    df = representative_fixture()
    df.loc[2, "provider_error"] = "EMPTY_RESPONSE"
    routed = route_asymmetric(df, 0.80, 0.80)
    assert routed.loc[2, "route"] == "HUMAN_REVIEW"


def test_lane_validation_and_safety_selection():
    validation = lane_threshold_validation(
        representative_fixture(),
        positive_fixture(),
        assisted_overrides={"b": 1, "f": 0},
        thresholds=(0.80, 0.95, 0.98),
    )
    selected = select_safety_constrained_thresholds(validation)

    assert selected["member_threshold"] == 0.98
    assert selected["not_member_threshold"] == 0.98


def test_cost_sensitivity_is_explicitly_normalized():
    profiles = {
        "balanced": {
            "wrong_member_cost": 7,
            "wrong_not_member_cost": 7,
            "review_cost": 1,
        }
    }
    grid = cost_sensitivity(
        representative_fixture(),
        profiles,
        thresholds=(0.80, 0.98),
    )
    assert set(grid["profile"]) == {"balanced"}
    assert grid["normalized_cost"].min() >= 0
