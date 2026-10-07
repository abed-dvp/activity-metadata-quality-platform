import json

import pandas as pd

from src.evaluation.semantic_report import evaluate_semantic_sample
from src.semantic.contracts import parse_semantic_decision
from src.semantic.prompt import build_category_prompt
from src.semantic.provider import _usage_tokens, _empty_response_fallback
from src.semantic.sample import build_calibration_sample


ONTOLOGY = {
    "museum": {
        "definition": "A place whose primary function is preserving, interpreting, or displaying collections or heritage for visitors.",
        "include": ["museums", "heritage interpretation sites"],
        "exclude": ["commercial art galleries", "framing shops"],
    }
}


def test_prompt_does_not_leak_ground_truth_or_baseline_prediction():
    row = pd.Series(
        {
            "entity_id": "x",
            "name": "Clock Gallery",
            "source_category": "attraction",
            "details": "",
            "review_text": "A specialist clock shop and repair service.",
            "is_member": 0,
            "prediction": 1,
        }
    )
    system, user = build_category_prompt(row, "museum", ONTOLOGY)
    payload = json.loads(user)
    assert "is_member" not in payload["entity"]
    assert "prediction" not in payload["entity"]
    assert "ground truth" in system.lower()


def test_strict_semantic_contract_accepts_uncertain():
    decision = parse_semantic_decision(
        {
            "decision": "uncertain",
            "confidence": 0.62,
            "reason_codes": ["INSUFFICIENT_EVIDENCE"],
            "evidence": "The reviews do not establish the venue's primary function.",
        }
    )
    assert decision.prediction is None
    assert decision.confidence == 0.62


def test_calibration_sample_covers_baseline_failure_strata():
    df = pd.DataFrame(
        {
            "entity_id": [str(i) for i in range(12)],
            "category": ["museum"] * 12,
            "is_member": [1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0],
            "prediction": [1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1],
        }
    )
    sample = build_calibration_sample(df, "museum", sample_size=8, seed=7)
    assert set(sample["baseline_stratum"]) == {
        "TRUE_POSITIVE",
        "FALSE_POSITIVE",
        "FALSE_NEGATIVE",
        "TRUE_NEGATIVE",
    }


def test_semantic_report_tracks_coverage_and_abstention():
    df = pd.DataFrame(
        {
            "is_member": [1, 0, 1, 0],
            "prediction": [0, 1, 0, 0],
            "semantic_decision": ["member", "not_member", "uncertain", "not_member"],
        }
    )
    report = evaluate_semantic_sample(df)
    assert report["coverage"] == 0.75
    assert report["abstention_rate"] == 0.25
    assert report["semantic_decided_only"]["precision"] == 1.0


def test_gemini_usage_parsing_from_dict_like_payload():
    class Interaction:
        usage = {
            "promptTokenCount": 100,
            "candidatesTokenCount": 25,
        }

    assert _usage_tokens(Interaction()) == (100, 25)


def test_empty_response_becomes_operational_abstention():
    class Candidate:
        finish_reason = "SAFETY"

    class Response:
        text = ""
        response_id = "r1"
        candidates = [Candidate()]
        usage = {
            "promptTokenCount": 12,
            "candidatesTokenCount": 0,
        }

    result = _empty_response_fallback(Response())
    assert result.decision.decision == "uncertain"
    assert result.decision.confidence == 0.0
    assert result.provider_error == "EMPTY_RESPONSE"
    assert "SAFETY" in result.decision.evidence
