from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from src.semantic.contracts import SemanticDecision, decision_json_schema, parse_semantic_decision


@dataclass(frozen=True)
class ProviderResult:
    decision: SemanticDecision
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None


class SemanticProvider(Protocol):
    model: str

    def evaluate(self, system_prompt: str, user_prompt: str) -> ProviderResult: ...


def _extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise ValueError("Responses API payload did not contain output text")


class OpenAIResponsesProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6-luna",
        timeout_seconds: int = 90,
        max_retries: int = 3,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def evaluate(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        body = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "category_membership_decision",
                    "schema": decision_json_schema(),
                    "strict": True,
                }
            },
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=self.timeout_seconds,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.HTTPError(
                        f"retryable OpenAI response {response.status_code}: {response.text[:500]}"
                    )
                response.raise_for_status()
                payload = response.json()
                decision = parse_semantic_decision(_extract_output_text(payload))
                usage = payload.get("usage") or {}
                return ProviderResult(
                    decision=decision,
                    response_id=payload.get("id"),
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                )
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == self.max_retries - 1:
                    break
                time.sleep(2**attempt)
        raise RuntimeError(f"Semantic provider failed after {self.max_retries} attempts: {last_error}")
