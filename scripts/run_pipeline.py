#!/usr/bin/env python3
"""Run the complete BI pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aibids.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate data, analytics marts, forecasts, and dashboards.")
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Reuse existing data/raw CSVs instead of regenerating synthetic raw data.",
    )
    args = parser.parse_args()
    result = run_pipeline(generate_raw=not args.skip_generate)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
