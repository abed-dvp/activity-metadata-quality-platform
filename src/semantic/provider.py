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

    for step in payload.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for content in step.get("content", []):
            if content.get("type") == "text" and isinstance(content.get("text"), str):
                return content["text"]

    for output in payload.get("output", []):
        for content in output.get("content", []):
            if isinstance(content.get("text"), str):
                return content["text"]

    raise ValueError("Gemini Interactions API payload did not contain output text")


def _usage_tokens(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = (
        payload.get("usage")
        or payload.get("usage_metadata")
        or payload.get("usageMetadata")
        or {}
    )
    input_tokens = (
        usage.get("input_tokens")
        or usage.get("inputTokenCount")
        or usage.get("promptTokenCount")
    )
    output_tokens = (
        usage.get("output_tokens")
        or usage.get("outputTokenCount")
        or usage.get("candidatesTokenCount")
    )
    return input_tokens, output_tokens


class GeminiInteractionsProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.8-flash",
        timeout_seconds: int = 90,
        max_retries: int = 3,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def evaluate(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        body = {
            "model": self.model,
            "input": (
                "SYSTEM INSTRUCTIONS:\n"
                f"{system_prompt}\n\n"
                "USER TASK:\n"
                f"{user_prompt}"
            ),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": decision_json_schema(),
            },
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    "https://generativelanguage.googleapis.com/v1beta/interactions",
                    headers={
                        "x-goog-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=self.timeout_seconds,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.HTTPError(
                        f"retryable Gemini response {response.status_code}: {response.text[:500]}"
                    )
                response.raise_for_status()
                payload = response.json()
                decision = parse_semantic_decision(_extract_output_text(payload))
                input_tokens, output_tokens = _usage_tokens(payload)
                return ProviderResult(
                    decision=decision,
                    response_id=payload.get("id"),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == self.max_retries - 1:
                    break
                time.sleep(2**attempt)

        raise RuntimeError(
            f"Gemini semantic provider failed after {self.max_retries} attempts: {last_error}"
        )
