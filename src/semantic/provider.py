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


class SemanticProvider(Protocol):
    model: str

    def evaluate(self, system_prompt: str, user_prompt: str) -> ProviderResult: ...


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _usage_tokens(interaction) -> tuple[int | None, int | None]:
    usage = (
        getattr(interaction, "usage", None)
        or getattr(interaction, "usage_metadata", None)
        or getattr(interaction, "usageMetadata", None)
    )
    if usage is None:
        return None, None

    def read(*names):
        for name in names:
            value = getattr(usage, name, None)
            if value is not None:
                return value
            if isinstance(usage, dict) and name in usage:
                return usage[name]
        return None

    return (
        _safe_int(read("input_tokens", "input_token_count", "prompt_token_count", "promptTokenCount")),
        _safe_int(read("output_tokens", "output_token_count", "candidates_token_count", "candidatesTokenCount")),
    )


class GeminiInteractionsProvider:
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

        for attempt in range(self.max_retries):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    system_instruction=system_prompt,
                    input=user_prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": decision_json_schema(),
                    },
                    generation_config={
                        "thinking_level": "low",
                    },
                )
                raw = interaction.output_text
                if not raw:
                    raise ValueError("Gemini returned an empty output_text")

                decision = parse_semantic_decision(raw)
                input_tokens, output_tokens = _usage_tokens(interaction)
                return ProviderResult(
                    decision=decision,
                    response_id=getattr(interaction, "id", None),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries - 1:
                    break
                time.sleep(2**attempt)

        raise RuntimeError(
            f"Gemini semantic provider failed after {self.max_retries} attempts: "
            f"{type(last_error).__name__}: {last_error}"
        )
