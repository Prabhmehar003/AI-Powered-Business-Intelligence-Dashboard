#!/usr/bin/env python3
"""Ask the local analytics Q&A engine a question."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aibids.qa import AnalyticsQA  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a business question over the processed BI marts.")
    parser.add_argument("question", nargs="+", help="Question to ask, wrapped in quotes.")
    args = parser.parse_args()
    answer = AnalyticsQA().answer(" ".join(args.question))
    print(json.dumps(answer, indent=2))


if __name__ == "__main__":
    main()
