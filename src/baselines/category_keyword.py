from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_CONFIG = ROOT / "config" / "category_baseline.yml"

TEXT_FIELDS = ("name", "source_category", "details", "review_text")
FIELD_WEIGHTS = {
    "name": 3.0,
    "source_category": 4.0,
    "details": 2.0,
    "review_text": 1.0,
}


@dataclass(frozen=True)
class BaselineConfig:
    aliases: dict[str, tuple[str, ...]]
    threshold: float = 2.0


def normalize_category(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"^category[_\s-]*", "", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.lower().strip())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", flags=re.IGNORECASE)


def default_terms(category: object) -> tuple[str, ...]:
    normalized = normalize_category(category)
    if not normalized:
        return tuple()
    terms = {normalized}
    tokens = [t for t in normalized.split() if len(t) >= 4]
    terms.update(tokens)
    return tuple(sorted(terms))


def load_config(path: Path = DEFAULT_CONFIG, threshold: float = 2.0) -> BaselineConfig:
    if not path.exists():
        return BaselineConfig(aliases={}, threshold=threshold)

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    aliases: dict[str, tuple[str, ...]] = {}
    for key, values in (raw.get("aliases") or {}).items():
        aliases[normalize_category(key)] = tuple(str(v).strip().lower() for v in values if str(v).strip())
    return BaselineConfig(aliases=aliases, threshold=threshold)


def terms_for_category(category: object, config: BaselineConfig) -> tuple[str, ...]:
    normalized = normalize_category(category)
    terms = set(default_terms(normalized))
    terms.update(config.aliases.get(normalized, ()))
    return tuple(sorted(t for t in terms if t))


def score_row(row: pd.Series, config: BaselineConfig) -> tuple[float, str]:
    terms = terms_for_category(row["category"], config)
    if not terms:
        return 0.0, ""

    score = 0.0
    evidence: list[str] = []
    for field in TEXT_FIELDS:
        value = row.get(field, "")
        if pd.isna(value):
            continue
        text = str(value)
        if not text.strip():
            continue

        matched_terms = [term for term in terms if _term_pattern(term).search(text)]
        if matched_terms:
            weight = FIELD_WEIGHTS[field]
            score += weight
            evidence.append(f"{field}:{'|'.join(sorted(set(matched_terms)))}")

    return score, "; ".join(evidence)


def predict_categories(df: pd.DataFrame, config: BaselineConfig) -> pd.DataFrame:
    required = {"entity_id", "category", "is_member"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()
    scores: list[float] = []
    evidences: list[str] = []
    for _, row in out.iterrows():
        score, evidence = score_row(row, config)
        scores.append(score)
        evidences.append(evidence)

    out["baseline_score"] = scores
    out["prediction"] = (out["baseline_score"] >= config.threshold).astype(int)
    out["prediction_method"] = "deterministic_keyword_v1"
    out["prediction_evidence"] = evidences
    out["threshold"] = config.threshold
    return out


def main(input_path: Path, output_path: Path, config_path: Path, threshold: float) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Missing evaluation dataset: {input_path}")

    config = load_config(config_path, threshold=threshold)
    predictions = predict_categories(pd.read_csv(input_path), config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_path, index=False)

    print(f"rows: {len(predictions):,}")
    print(f"entities: {predictions['entity_id'].nunique():,}")
    print(f"categories: {predictions['category'].nunique():,}")
    print(f"predicted positives: {int(predictions['prediction'].sum()):,}")
    print(f"threshold: {threshold}")
    print(f"saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the deterministic category baseline.")
    parser.add_argument("--input", type=Path, default=PROCESSED_DIR / "category_evaluation.csv")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "category_predictions.csv")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--threshold", type=float, default=2.0)
    args = parser.parse_args()
    main(args.input, args.output, args.config, args.threshold)
