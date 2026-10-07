from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "datasets.yml"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "raw"


class DownloadError(RuntimeError):
    """Raised when every configured source URL fails."""


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)["london_pois"]


def download_file(urls: Iterable[str], output_path: Path) -> str:
    """Download a file from the first working URL and return the successful URL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    for url in urls:
        tmp_path = output_path.with_suffix(output_path.suffix + ".part")
        try:
            with requests.get(
                url,
                stream=True,
                timeout=120,
                headers={"User-Agent": "activity-metadata-quality-platform/0.1"},
            ) as response:
                response.raise_for_status()
                with tmp_path.open("wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            if tmp_path.stat().st_size == 0:
                raise DownloadError(f"empty response from {url}")

            tmp_path.replace(output_path)
            return url
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            tmp_path.unlink(missing_ok=True)

    raise DownloadError(
        f"Could not download {output_path.name}. Tried:\n- " + "\n- ".join(errors)
    )


def main(output_dir: Path, force: bool = False) -> None:
    config = load_config()
    for file_config in config["files"].values():
        target = output_dir / file_config["filename"]
        if target.exists() and target.stat().st_size > 0 and not force:
            print(f"skip: {target.name} already exists")
            continue

        print(f"download: {target.name}")
        source = download_file(file_config["urls"], target)
        print(f"saved: {target} ({target.stat().st_size:,} bytes)")
        print(f"source: {source}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the London tourism POI dataset.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for raw CSV files.",
    )
    parser.add_argument("--force", action="store_true", help="Re-download existing files.")
    args = parser.parse_args()
    main(args.output_dir, force=args.force)
