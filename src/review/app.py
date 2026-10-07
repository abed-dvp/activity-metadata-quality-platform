from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from src.review.adjudication import make_adjudication, upsert_adjudication
from src.review.queue import build_review_queue
from src.semantic.prompt import review_snippets


def _load_adjudications(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    import streamlit as st

    input_path = Path(
        os.getenv(
            "REVIEW_INPUT",
            "data/processed/semantic_museum_v1_calibration.csv",
        )
    )
    output_path = Path(
        os.getenv(
            "ADJUDICATION_OUTPUT",
            "data/processed/museum_adjudications.csv",
        )
    )
    reviewer_id = os.getenv("REVIEWER_ID", "reviewer")

    st.set_page_config(
        page_title="Metadata Quality Adjudication",
        layout="wide",
    )
    st.title("Metadata Quality — Human Adjudication")
    st.caption(
        "Blind-first review: judge the entity before seeing the public label "
        "or Gemini decision."
    )

    if not input_path.exists():
        st.error(f"Missing calibration file: {input_path}")
        st.stop()

    calibration = pd.read_csv(input_path)
    queue = build_review_queue(calibration)
    existing = _load_adjudications(output_path)

    reviewed_ids = (
        set(existing["review_case_id"].astype(str))
        if not existing.empty and "review_case_id" in existing.columns
        else set()
    )
    pending = queue.loc[
        ~queue["review_case_id"].astype(str).isin(reviewed_ids)
    ].reset_index(drop=True)

    st.metric("Reviewed", f"{len(reviewed_ids)} / {len(queue)}")

    if pending.empty:
        st.success("All queued cases have been adjudicated.")
        st.stop()

    row = pending.iloc[0]
    case_id = str(row["review_case_id"])
    locked_key = f"blind::{case_id}"

    st.subheader(row["name"])
    cols = st.columns(2)

    with cols[0]:
        st.write("**Source category**", row.get("source_category", ""))
        st.write("**Address**", row.get("address", ""))
        st.write("**Details**")
        st.write(row.get("details", "") or "—")

    with cols[1]:
        st.write("**Review evidence**")
        st.write(review_snippets(row.get("review_text", "")) or "—")

    if locked_key not in st.session_state:
        st.markdown("### 1. Blind judgement")
        label = st.radio(
            "Final category judgement",
            ["member", "not_member", "ambiguous"],
            horizontal=True,
        )
        confidence = st.slider(
            "Reviewer confidence",
            0.0,
            1.0,
            0.90,
            0.05,
        )
        notes = st.text_area(
            "Notes",
            placeholder="Evidence, ambiguity, or ontology concern...",
        )

        if st.button("Lock blind judgement", type="primary"):
            st.session_state[locked_key] = {
                "label": label,
                "confidence": confidence,
                "notes": notes,
            }
            st.rerun()

        st.stop()

    locked = st.session_state[locked_key]

    st.markdown("### 2. Reveal and classify disagreement")
    reveal = st.columns(3)
    reveal[0].metric(
        "Public label",
        "member" if int(row["is_member"]) == 1 else "not_member",
    )
    reveal[1].metric("Gemini", str(row["semantic_decision"]))
    reveal[2].metric(
        "Gemini confidence",
        f"{float(row['semantic_confidence']):.2f}",
    )

    st.write("**Gemini evidence**", row.get("semantic_evidence", ""))
    st.info(
        f"Your blind judgement: {locked['label']} "
        f"({locked['confidence']:.2f})"
    )

    resolution = st.selectbox(
        "Resolution type",
        [
            "MODEL_ERROR",
            "PUBLIC_LABEL_ERROR",
            "ONTOLOGY_MISMATCH",
            "INSUFFICIENT_EVIDENCE",
            "AGREEMENT_AFTER_REVIEW",
        ],
    )

    if st.button("Finalize adjudication", type="primary"):
        record = make_adjudication(
            review_case_id=case_id,
            reviewer_label=locked["label"],
            reviewer_confidence=locked["confidence"],
            resolution_type=resolution,
            reviewer_notes=locked["notes"],
            reviewer_id=reviewer_id,
        )
        upsert_adjudication(output_path, record)
        del st.session_state[locked_key]
        st.rerun()


if __name__ == "__main__":
    main()
