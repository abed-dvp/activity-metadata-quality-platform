from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.quality.location import summarize_location_quality, validate_location_quality

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def main(catalog_path: Path, findings_path: Path, summary_path: Path) -> None:
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"Missing {catalog_path}. Run `python -m src.data.run_phase1` first."
        )

    catalog = pd.read_csv(catalog_path)
    findings = validate_location_quality(catalog)
    summary = summarize_location_quality(catalog, findings)

    findings_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    findings.to_csv(findings_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"findings: {findings_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the deterministic London location-quality baseline.")
    parser.add_argument("--catalog", type=Path, default=PROCESSED / "catalog.csv")
    parser.add_argument("--findings", type=Path, default=PROCESSED / "location_findings.csv")
    parser.add_argument("--summary", type=Path, default=PROCESSED / "location_summary.json")
    args = parser.parse_args()
    main(args.catalog, args.findings, args.summary)
