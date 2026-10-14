from __future__ import annotations

import argparse
from pathlib import Path

from src.demo.end_to_end import DEFAULT_ENTITY_ID, run_demo, write_demo

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "reports" / "demo" / "end_to_end_demo.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "demo" / "end_to_end_demo.md"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a cached, zero-cost end-to-end metadata quality demo."
    )
    parser.add_argument("--entity-id", default=DEFAULT_ENTITY_ID)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    trace = run_demo(entity_id=args.entity_id)
    write_demo(trace, args.json, args.markdown)

    print(args.markdown.read_text(encoding="utf-8"))
    print(f"json: {args.json}")
    print(f"markdown: {args.markdown}")
