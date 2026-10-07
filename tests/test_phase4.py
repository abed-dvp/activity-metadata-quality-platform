from pathlib import Path

import pandas as pd

from src.review.queue import build_review_queue, review_queue_summary
from src.review.adjudication import (
    make_adjudication,
    merge_adjudications,
    upsert_adjudication,
)
from src.review.gold import build_adjudicated_gold, build_regression_set
from src.evaluation.routing import route_semantic_decisions, threshold_sweep


def fixture():
    return pd.DataFrame({
        "entity_id": ["a", "b", "c", "d"],
        "name": ["A", "B", "C", "D"],
        "address": ["x"] * 4,
        "source_category": ["attraction"] * 4,
        "details": ["details"] * 4,
        "review_text": ["reviews"] * 4,
        "category": ["museum"] * 4,
        "is_member": [1, 0, 1, 0],
        "semantic_decision": ["member", "member", "uncertain", "not_member"],
        "semantic_confidence": [0.98, 0.96, 0.6, 0.99],
        "semantic_reason_codes": ["[]"] * 4,
        "semantic_evidence": ["x"] * 4,
    })


def test_review_queue_only_contains_unresolved_cases():
    queue = build_review_queue(fixture())
    assert len(queue) == 2
    assert set(queue["review_reason"]) == {
        "HIGH_CONFIDENCE_LABEL_CONFLICT",
        "UNCERTAIN",
    }
    assert review_queue_summary(queue)["review_cases"] == 2


def test_adjudication_becomes_gold_and_regression_case():
    queue = build_review_queue(fixture())
    record = make_adjudication(
        queue.iloc[0]["review_case_id"],
        "not_member",
        0.95,
        "MODEL_ERROR",
        "checked",
        "reviewer-1",
    )
    reviewed = merge_adjudications(
        queue,
        pd.DataFrame([record.to_dict()]),
    )
    gold = build_adjudicated_gold(reviewed)
    regression = build_regression_set(reviewed)

    assert len(gold) == 1
    assert gold.iloc[0]["adjudicated_label"] == 0
    assert gold.iloc[0]["label_origin"] == "human_adjudication"
    assert len(regression) == 1
    assert regression.iloc[0]["expected_label"] == 0


def test_upsert_keeps_one_final_record_per_case(tmp_path: Path):
    path = tmp_path / "adjudications.csv"
    first = make_adjudication(
        "a::museum",
        "member",
        0.8,
        "AGREEMENT_AFTER_REVIEW",
        reviewer_id="r1",
    )
    second = make_adjudication(
        "a::museum",
        "not_member",
        0.9,
        "MODEL_ERROR",
        reviewer_id="r1",
    )

    upsert_adjudication(path, first)
    upsert_adjudication(path, second)

    df = pd.read_csv(path)
    assert len(df) == 1
    assert df.iloc[0]["reviewer_label"] == "not_member"


def test_routing_and_threshold_sweep():
    df = fixture()
    routed = route_semantic_decisions(df, 0.95, 0.95)
    assert list(routed["route"]) == [
        "AUTO_MEMBER",
        "AUTO_MEMBER",
        "HUMAN_REVIEW",
        "AUTO_NOT_MEMBER",
    ]

    sweep = threshold_sweep(df, thresholds=(0.95, 0.99))
    assert len(sweep) == 2
    assert sweep.iloc[0]["auto_rows"] == 3
    assert sweep.iloc[0]["auto_errors"] == 1
