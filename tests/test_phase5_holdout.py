import pandas as pd

from src.evaluation.holdout import build_representative_holdout


def test_holdout_excludes_calibration_and_preserves_positive_diagnostic():
    df = pd.DataFrame({
        "entity_id": [str(i) for i in range(10)],
        "category": ["museum"] * 10,
        "is_member": [1, 0, 0, 1, 0, 0, 1, 0, 0, 0],
        "prediction": [0] * 10,
    })
    union, summary = build_representative_holdout(
        predictions=df,
        calibration_entity_ids={"0", "1"},
        category="museum",
        representative_size=4,
        seed=1,
    )

    assert not set(union["entity_id"]).intersection({"0", "1"})
    assert summary["residual_rows"] == 8
    assert summary["residual_positive_rows"] == 2
    assert summary["representative_rows"] == 4

    positive_ids = set(
        union.loc[union["in_positive_diagnostic"], "entity_id"]
    )
    assert positive_ids == {"3", "6"}
    assert len(union) <= 6
