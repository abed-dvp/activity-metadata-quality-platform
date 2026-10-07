import pandas as pd

from src.data.prepare_category_ground_truth import normalize_columns, detect_identity_columns


def test_normalize_columns():
    df = pd.DataFrame(columns=["POI Name", "Full-Address", "Museums"])
    out = normalize_columns(df)
    assert list(out.columns) == ["poi_name", "full_address", "museums"]


def test_detect_identity_columns():
    df = pd.DataFrame(columns=["poi_name", "address", "museum"])
    assert detect_identity_columns(df) == ("poi_name", "address")
