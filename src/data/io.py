from __future__ import annotations

from pathlib import Path

import pandas as pd

CANDIDATE_DELIMITERS = (",", ";", "\t", "|")


def detect_delimiter(path: Path) -> str:
    """Infer a simple tabular delimiter from the header row.

    The London source contains very long review fields, so using pandas' default
    comma parser without checking the actual delimiter can produce thousands of
    apparent columns. The header is sufficient because field names themselves do
    not contain the delimiter.
    """
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        header = f.readline()

    if not header:
        raise ValueError(f"Empty source file: {path}")

    counts = {delimiter: header.count(delimiter) for delimiter in CANDIDATE_DELIMITERS}
    delimiter, count = max(counts.items(), key=lambda item: item[1])

    if count == 0:
        raise ValueError(
            f"Could not infer delimiter for {path}. Header preview: {header[:200]!r}"
        )
    return delimiter


def read_source_csv(path: Path) -> pd.DataFrame:
    delimiter = detect_delimiter(path)
    return pd.read_csv(
        path,
        sep=delimiter,
        encoding="utf-8-sig",
        engine="python",
    )
