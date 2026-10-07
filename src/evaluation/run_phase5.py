from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.evaluation.holdout import (
    build_representative_holdout,
    positive_diagnostic_view,
    representative_view,
)
from src.evaluation.metrics import binary_metrics
from src.evaluation.routing import threshold_sweep
from src.semantic.prompt import PROMPT_VERSION, build_category_prompt, load_ontology
from src.semantic.provider import GeminiGenerateContentProvider, SemanticProvider
from src.semantic.sample import build_calibration_sample

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports" / "phase5"


def _prompt_hash(system_prompt: str, user_prompt: str) -> str:
    return hashlib.sha256((system_prompt + "\n" + user_prompt).encode("utf-8")).hexdigest()[:16]


def _evaluate_one(provider: SemanticProvider, row: pd.Series, category: str, ontology: dict) -> dict:
    system_prompt, user_prompt = build_category_prompt(row, category, ontology)
    result = provider.evaluate(system_prompt, user_prompt)
    decision = result.decision
    return {
        "entity_id": str(row["entity_id"]),
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


def _semantic_metrics(df: pd.DataFrame) -> dict:
    decided = df.loc[df["semantic_decision"] != "uncertain"].copy()
    decided["semantic_prediction"] = decided["semantic_decision"].map(
        {"member": 1, "not_member": 0}
    ).astype(int)

    metrics = binary_metrics(
        decided["is_member"].astype(int).tolist(),
        decided["semantic_prediction"].astype(int).tolist(),
    ) if len(decided) else binary_metrics([], [])

    conservative = df["semantic_decision"].map(
        {"member": 1, "not_member": 0, "uncertain": 0}
    ).astype(int)
    conservative_metrics = binary_metrics(
        df["is_member"].astype(int).tolist(),
        conservative.tolist(),
    )

    return {
        "rows": int(len(df)),
        "decided_rows": int(len(decided)),
        "coverage": float(len(decided) / len(df)) if len(df) else 0.0,
        "abstention_rate": float((df["semantic_decision"] == "uncertain").mean()) if len(df) else 0.0,
        "decided_only": metrics.to_dict(),
        "conservative": conservative_metrics.to_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 5 representative holdout validation.")
    parser.add_argument("--predictions", type=Path, default=PROCESSED / "category_predictions.csv")
    parser.add_argument("--category", default="museum")
    parser.add_argument("--representative-size", type=int, default=600)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    parser.add_argument("--max-workers", type=int, default=5)
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")
    if not args.predictions.exists():
        raise FileNotFoundError("Phase 2 predictions are required")

    predictions = pd.read_csv(args.predictions)
    frozen_calibration = build_calibration_sample(
        predictions,
        category=args.category,
        sample_size=240,
        seed=42,
    )
    calibration_ids = set(frozen_calibration["entity_id"].astype(str))

    holdout, design = build_representative_holdout(
        predictions=predictions,
        calibration_entity_ids=calibration_ids,
        category=args.category,
        representative_size=args.representative_size,
        seed=args.seed,
    )

    ontology = load_ontology()
    provider = GeminiGenerateContentProvider(api_key=api_key, model=args.model)

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {
            pool.submit(_evaluate_one, provider, row, args.category, ontology): i
            for i, row in holdout.iterrows()
        }
        for future in as_completed(futures):
            results.append(future.result())

    result_df = pd.DataFrame(results)
    evaluated = holdout.merge(
        result_df,
        on=["entity_id", "category"],
        how="left",
        validate="one_to_one",
    )

    representative = representative_view(evaluated)
    positives = positive_diagnostic_view(evaluated)

    representative_metrics = _semantic_metrics(representative)
    positive_recall = {
        "rows": int(len(positives)),
        "member": int((positives["semantic_decision"] == "member").sum()),
        "not_member": int((positives["semantic_decision"] == "not_member").sum()),
        "uncertain": int((positives["semantic_decision"] == "uncertain").sum()),
        "member_rate": float((positives["semantic_decision"] == "member").mean()) if len(positives) else 0.0,
        "member_or_uncertain_rate": float(
            positives["semantic_decision"].isin(["member", "uncertain"]).mean()
        ) if len(positives) else 0.0,
    }

    sweep = threshold_sweep(representative)

    input_tokens = int(pd.to_numeric(evaluated["input_tokens"], errors="coerce").fillna(0).sum())
    output_tokens = int(pd.to_numeric(evaluated["output_tokens"], errors="coerce").fillna(0).sum())
    estimated_cost_usd = input_tokens / 1_000_000 * 0.75 + output_tokens / 1_000_000 * 3.75

    summary = {
        "phase": "phase5_representative_holdout",
        "category": args.category,
        "model": args.model,
        "provider": "google_gemini_generate_content",
        "prompt_version": PROMPT_VERSION,
        "holdout_design": design,
        "representative_metrics": representative_metrics,
        "positive_diagnostic": positive_recall,
        "input_tokens": input_tokens,
        "output_tokens_including_thinking": output_tokens,
        "estimated_standard_cost_usd_oct_2026": estimated_cost_usd,
        "important_caveat": (
            "Public annotations remain the evaluation reference for holdout metrics, "
            "but Phase 4 showed likely annotation/ontology mismatches. These metrics are "
            "therefore validation against the public-label reference, not final human gold."
        ),
    }

    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(PROCESSED / "museum_phase5_holdout_evaluated.csv", index=False)
    representative.to_csv(PROCESSED / "museum_phase5_representative.csv", index=False)
    positives.to_csv(PROCESSED / "museum_phase5_positive_diagnostic.csv", index=False)
    sweep.to_csv(REPORTS / "routing_threshold_sweep_holdout.csv", index=False)
    (REPORTS / "holdout_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    print(sweep.to_string(index=False))


if __name__ == "__main__":
    main()
