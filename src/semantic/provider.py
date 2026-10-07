from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from google import genai

from src.semantic.contracts import SemanticDecision, decision_json_schema, parse_semantic_decision


@dataclass(frozen=True)
class ProviderResult:
    decision: SemanticDecision
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    provider_error: str | None = None


class SemanticProvider(Protocol):
    model: str

    def evaluate(self, system_prompt: str, user_prompt: str) -> ProviderResult: ...


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _usage_tokens(response) -> tuple[int | None, int | None]:
    usage = (
        getattr(response, "usage_metadata", None)
        or getattr(response, "usageMetadata", None)
        or getattr(response, "usage", None)
        or {}
    )

    def read(*names):
        for name in names:
            value = getattr(usage, name, None)
            if value is not None:
                return value
            if isinstance(usage, dict) and name in usage:
                return usage[name]
        return None

    prompt = _safe_int(read("prompt_token_count", "promptTokenCount", "input_tokens"))
    candidates = _safe_int(read("candidates_token_count", "candidatesTokenCount", "output_tokens"))
    thoughts = _safe_int(read("thoughts_token_count", "thoughtsTokenCount")) or 0

    output = None if candidates is None and thoughts == 0 else (candidates or 0) + thoughts
    return prompt, output


def _finish_reason(response) -> str | None:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    reason = getattr(candidates[0], "finish_reason", None) or getattr(candidates[0], "finishReason", None)
    return str(reason) if reason is not None else None


def _empty_response_fallback(response) -> ProviderResult:
    input_tokens, output_tokens = _usage_tokens(response)
    finish_reason = _finish_reason(response)
    suffix = f" finish_reason={finish_reason}" if finish_reason else ""
    return ProviderResult(
        decision=SemanticDecision(
            decision="uncertain",
            confidence=0.0,
            reason_codes=("INSUFFICIENT_EVIDENCE",),
            evidence=(
                "Gemini returned no usable text after retries; "
                "route this case to human review." + suffix
            ),
        ),
        response_id=getattr(response, "response_id", None),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider_error="EMPTY_RESPONSE",
    )


class GeminiGenerateContentProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.8-flash",
        max_retries: int = 3,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.client = genai.Client(api_key=api_key)

    def evaluate(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        last_error: Exception | None = None
        last_empty_response = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config={
                        "system_instruction": system_prompt,
                        "response_mime_type": "application/json",
                        "response_json_schema": decision_json_schema(),
                        "thinking_config": {
                            "thinking_level": "low",
                        },
                    },
                )

                raw = response.text
                if not raw:
                    last_empty_response = response
                    if attempt == self.max_retries - 1:
                        return _empty_response_fallback(response)
                    time.sleep(2**attempt)
                    continue

                decision = parse_semantic_decision(raw)
                input_tokens, output_tokens = _usage_tokens(response)
                return ProviderResult(
                    decision=decision,
                    response_id=getattr(response, "response_id", None),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    provider_error=None,
                )
            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries - 1:
                    break
                time.sleep(2**attempt)

        if last_empty_response is not None and last_error is None:
            return _empty_response_fallback(last_empty_response)

        raise RuntimeError(
            f"Gemini semantic provider failed after {self.max_retries} attempts: "
            f"{type(last_error).__name__}: {last_error}"
        )
