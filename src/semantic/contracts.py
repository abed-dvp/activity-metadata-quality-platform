from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

DECISIONS = ("member", "not_member", "uncertain")
REASON_CODES = (
    "PRIMARY_FUNCTION_MATCH",
    "ENTITY_TYPE_MATCH",
    "CONTEXT_MATCH",
    "ADJACENT_CATEGORY_ONLY",
    "CONTRADICTORY_EVIDENCE",
    "INSUFFICIENT_EVIDENCE",
)


@dataclass(frozen=True)
class SemanticDecision:
    decision: str
    confidence: float
    reason_codes: tuple[str, ...]
    evidence: str

    @property
    def prediction(self) -> int | None:
        if self.decision == "member":
            return 1
        if self.decision == "not_member":
            return 0
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "evidence": self.evidence,
        }


def decision_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": list(DECISIONS)},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason_codes": {
                "type": "array",
                "items": {"type": "string", "enum": list(REASON_CODES)},
                "minItems": 1,
                "maxItems": 3,
            },
            "evidence": {"type": "string"},
        },
        "required": ["decision", "confidence", "reason_codes", "evidence"],
        "additionalProperties": False,
    }


def parse_semantic_decision(raw: str | dict[str, Any]) -> SemanticDecision:
    payload = json.loads(raw) if isinstance(raw, str) else dict(raw)
    expected = {"decision", "confidence", "reason_codes", "evidence"}
    if set(payload) != expected:
        raise ValueError(f"Semantic output must contain exactly {sorted(expected)}")

    decision = payload["decision"]
    if decision not in DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")

    confidence = float(payload["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    reason_codes = tuple(payload["reason_codes"])
    if not 1 <= len(reason_codes) <= 3:
        raise ValueError("reason_codes must contain 1 to 3 items")
    invalid = set(reason_codes) - set(REASON_CODES)
    if invalid:
        raise ValueError(f"Invalid reason codes: {sorted(invalid)}")

    evidence = str(payload["evidence"]).strip()
    if not evidence:
        raise ValueError("evidence must not be empty")

    return SemanticDecision(decision, confidence, reason_codes, evidence)
