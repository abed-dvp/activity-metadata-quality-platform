from pathlib import Path

from src.data.io import detect_delimiter, read_source_csv


def test_detects_semicolon_delimiter(tmp_path: Path):
    path = tmp_path / "sample.csv"
    path.write_text("id;name;address\n1;Museum;London\n", encoding="utf-8")
    assert detect_delimiter(path) == ";"
    df = read_source_csv(path)
    assert list(df.columns) == ["id", "name", "address"]
    assert len(df) == 1


def test_detects_comma_delimiter(tmp_path: Path):
    path = tmp_path / "sample.csv"
    path.write_text('id,name,address\n1,"Museum, London",London\n', encoding="utf-8")
    assert detect_delimiter(path) == ","
    df = read_source_csv(path)
    assert list(df.columns) == ["id", "name", "address"]
    assert len(df) == 1
