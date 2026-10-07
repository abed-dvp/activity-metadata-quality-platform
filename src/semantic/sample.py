from __future__ import annotations

import pandas as pd


def _stratum(row: pd.Series) -> str:
    truth = int(row["is_member"])
    pred = int(row["prediction"])
    if truth == 1 and pred == 1:
        return "TRUE_POSITIVE"
    if truth == 0 and pred == 1:
        return "FALSE_POSITIVE"
    if truth == 1 and pred == 0:
        return "FALSE_NEGATIVE"
    return "TRUE_NEGATIVE"


def build_calibration_sample(
    predictions: pd.DataFrame,
    category: str,
    sample_size: int = 240,
    seed: int = 42,
) -> pd.DataFrame:
    source = predictions.loc[predictions["category"] == category].copy()
    if source.empty:
        raise ValueError(f"No rows found for category {category!r}")
    source["baseline_stratum"] = source.apply(_stratum, axis=1)

    target_each = max(1, sample_size // 4)
    selected: list[pd.DataFrame] = []
    used: set[int] = set()

    for stratum in ("FALSE_NEGATIVE", "FALSE_POSITIVE", "TRUE_POSITIVE", "TRUE_NEGATIVE"):
        group = source.loc[source["baseline_stratum"] == stratum]
        take = min(target_each, len(group))
        if take:
            part = group.sample(n=take, random_state=seed)
            selected.append(part)
            used.update(part.index.tolist())

    sample = pd.concat(selected, ignore_index=False) if selected else source.iloc[0:0]
    remaining = sample_size - len(sample)
    if remaining > 0:
        pool = source.loc[~source.index.isin(used)]
        take = min(remaining, len(pool))
        if take:
            sample = pd.concat([sample, pool.sample(n=take, random_state=seed + 1)])

    return (
        sample.sample(frac=1, random_state=seed + 2)
        .head(sample_size)
        .reset_index(drop=True)
    )
