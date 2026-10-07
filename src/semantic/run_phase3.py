from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.evaluation.semantic_report import evaluate_semantic_sample
from src.semantic.prompt import PROMPT_VERSION, build_category_prompt, load_ontology
from src.semantic.provider import OpenAIResponsesProvider, SemanticProvider
from src.semantic.sample import build_calibration_sample

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def _prompt_hash(system_prompt: str, user_prompt: str) -> str:
    return hashlib.sha256((system_prompt + "\n" + user_prompt).encode("utf-8")).hexdigest()[:16]


def _evaluate_one(provider: SemanticProvider, row: pd.Series, category: str, ontology: dict) -> dict:
    system_prompt, user_prompt = build_category_prompt(row, category, ontology)
    result = provider.evaluate(system_prompt, user_prompt)
    decision = result.decision
    return {
        "entity_id": row["entity_id"],
        "category": category,
        "semantic_decision": decision.decision,
        "semantic_confidence": decision.confidence,
        "semantic_reason_codes": json.dumps(list(decision.reason_codes)),
        "semantic_evidence": decision.evidence,
        "semantic_prediction": decision.prediction,
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": _prompt_hash(system_prompt, user_prompt),
        "model": provider.model,
        "provider_response_id": result.response_id,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


def run_semantic_evaluation(
    predictions: pd.DataFrame,
    provider: SemanticProvider,
    category: str,
    sample_size: int,
    max_workers: int,
) -> tuple[pd.DataFrame, dict]:
    ontology = load_ontology()
    sample = build_calibration_sample(predictions, category, sample_size=sample_size)

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_evaluate_one, provider, row, category, ontology): i
            for i, row in sample.iterrows()
        }
        for future in as_completed(futures):
            results.append(future.result())

    result_df = pd.DataFrame(results)
    merged = sample.merge(result_df, on=["entity_id", "category"], how="left", validate="one_to_one")
    summary = evaluate_semantic_sample(merged)
    summary.update(
        {
            "category": category,
            "sample_size": int(len(merged)),
            "model": provider.model,
            "prompt_version": PROMPT_VERSION,
            "input_tokens": int(pd.to_numeric(merged["input_tokens"], errors="coerce").fillna(0).sum()),
            "output_tokens": int(pd.to_numeric(merged["output_tokens"], errors="coerce").fillna(0).sum()),
        }
    )
    return merged, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 3 atomic semantic category evaluation.")
    parser.add_argument("--category", default="museum")
    parser.add_argument("--sample-size", type=int, default=240)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"))
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--input", type=Path, default=PROCESSED / "category_predictions.csv")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Missing {args.input}. Run Phase 1 and Phase 2 first."
        )
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it as a local environment variable or GitHub Actions secret."
        )

    predictions = pd.read_csv(args.input)
    provider = OpenAIResponsesProvider(api_key=api_key, model=args.model)
    evaluated, summary = run_semantic_evaluation(
        predictions=predictions,
        provider=provider,
        category=args.category,
        sample_size=args.sample_size,
        max_workers=args.max_workers,
    )

    PROCESSED.mkdir(parents=True, exist_ok=True)
    stem = f"semantic_{args.category}_v1"
    evaluated.to_csv(PROCESSED / f"{stem}_calibration.csv", index=False)
    (PROCESSED / f"{stem}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    disagreements = evaluated.loc[
        evaluated["prediction"] != evaluated["semantic_prediction"].fillna(-1)
    ].copy()
    disagreements.to_csv(PROCESSED / f"{stem}_disagreements.csv", index=False)

    print(json.dumps(summary, indent=2))
    print(f"saved: {PROCESSED / f'{stem}_calibration.csv'}")


if __name__ == "__main__":
    main()
