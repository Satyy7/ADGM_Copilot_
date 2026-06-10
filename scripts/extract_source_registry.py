"""Extract the official source registry from Data Sources.docx."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.source_registry import (
    extract_source_manifest,
    save_source_manifest,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("Data Sources.docx"),
        help="Path to the DOCX source registry.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/source_registry.json"),
        help="Path for the normalized source manifest JSON.",
    )
    return parser.parse_args()


def main() -> None:
    """Extract and save the source registry."""

    args = parse_args()
    manifest = extract_source_manifest(args.input)
    save_source_manifest(manifest, args.output)
    print(f"Wrote {len(manifest.sources)} sources to {args.output}")


if __name__ == "__main__":
    main()
