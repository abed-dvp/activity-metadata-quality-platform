from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ONTOLOGY = ROOT / "config" / "category_ontology.yml"
PROMPT_VERSION = "category_membership_v1"


def load_ontology(path: Path = DEFAULT_ONTOLOGY) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload["categories"]


def _clean(value: Any) -> str:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return ""
    return str(value).strip()


def review_snippets(value: Any, max_reviews: int = 6, max_chars: int = 3500) -> str:
    text = _clean(value)
    if not text:
        return ""

    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text[:max_chars]

    snippets: list[str] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and item.get("text"):
                snippets.append(str(item["text"]).strip())
            if len(snippets) >= max_reviews:
                break
    if not snippets:
        return text[:max_chars]
    return "\n---\n".join(snippets)[:max_chars]


def build_category_prompt(row: pd.Series | dict[str, Any], category: str, ontology: dict[str, Any]) -> tuple[str, str]:
    if category not in ontology:
        raise KeyError(f"Category {category!r} is not defined in the ontology")

    spec = ontology[category]
    system = (
        "You are an atomic travel-catalog category evaluator. Evaluate exactly one category for one entity. "
        "Follow the supplied business definition, including inclusion and exclusion boundaries. "
        "Use only the entity metadata supplied in this request. Do not infer labels from popularity, rating, or the dataset's ground truth. "
        "Choose 'uncertain' when available evidence is insufficient or materially contradictory. "
        "Return only JSON matching the required schema."
    )

    safe = {
        "name": _clean(row.get("name", "")),
        "source_category": _clean(row.get("source_category", "")),
        "details": _clean(row.get("details", ""))[:2500],
        "review_snippets": review_snippets(row.get("review_text", "")),
    }
    user = {
        "task": "Decide whether this entity belongs to the target category.",
        "target_category": category,
        "category_definition": spec["definition"],
        "include_when": spec.get("include", []),
        "exclude_when": spec.get("exclude", []),
        "entity": safe,
        "decision_policy": {
            "member": "The available evidence supports membership under the definition.",
            "not_member": "The evidence supports a different primary type or an explicit exclusion boundary.",
            "uncertain": "The metadata is insufficient or contradictory enough that a reviewer should decide.",
        },
    }
    return system, json.dumps(user, ensure_ascii=False, indent=2)
