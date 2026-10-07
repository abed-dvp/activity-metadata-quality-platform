from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd

ReviewerLabel = Literal["member", "not_member", "ambiguous"]
ResolutionType = Literal[
    "MODEL_ERROR",
    "PUBLIC_LABEL_ERROR",
    "ONTOLOGY_MISMATCH",
    "INSUFFICIENT_EVIDENCE",
    "AGREEMENT_AFTER_REVIEW",
]


@dataclass(frozen=True)
class Adjudication:
    review_case_id: str
    reviewer_label: ReviewerLabel
    reviewer_confidence: float
    resolution_type: ResolutionType
    reviewer_notes: str
    reviewer_id: str
    reviewed_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def make_adjudication(
    review_case_id: str,
    reviewer_label: ReviewerLabel,
    reviewer_confidence: float,
    resolution_type: ResolutionType,
    reviewer_notes: str = "",
    reviewer_id: str = "anonymous",
) -> Adjudication:
    if reviewer_label not in {"member", "not_member", "ambiguous"}:
        raise ValueError("Invalid reviewer_label")
    if resolution_type not in {
        "MODEL_ERROR", "PUBLIC_LABEL_ERROR", "ONTOLOGY_MISMATCH",
        "INSUFFICIENT_EVIDENCE", "AGREEMENT_AFTER_REVIEW",
    }:
        raise ValueError("Invalid resolution_type")
    if not 0 <= float(reviewer_confidence) <= 1:
        raise ValueError("reviewer_confidence must be between 0 and 1")
    return Adjudication(
        review_case_id=review_case_id,
        reviewer_label=reviewer_label,
        reviewer_confidence=float(reviewer_confidence),
        resolution_type=resolution_type,
        reviewer_notes=str(reviewer_notes).strip(),
        reviewer_id=str(reviewer_id).strip() or "anonymous",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )


def merge_adjudications(queue: pd.DataFrame, adjudications: pd.DataFrame) -> pd.DataFrame:
    required = {"review_case_id", "reviewer_label", "reviewer_confidence", "resolution_type"}
    missing = required - set(adjudications.columns)
    if missing:
        raise ValueError(f"Missing adjudication columns: {sorted(missing)}")
    if adjudications["review_case_id"].duplicated().any():
        raise ValueError("Each review_case_id can have at most one final adjudication")
    return queue.merge(adjudications, on="review_case_id", how="left", validate="one_to_one")


def upsert_adjudication(path: Path | str, record: Adjudication) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        current = pd.read_csv(path)
    else:
        current = pd.DataFrame()

    row = pd.DataFrame([record.to_dict()])
    if current.empty:
        out = row
    else:
        current = current.loc[
            current["review_case_id"].astype(str) != record.review_case_id
        ]
        out = pd.concat([current, row], ignore_index=True)
    out.to_csv(path, index=False)
