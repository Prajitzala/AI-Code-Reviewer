#!/usr/bin/env python3
"""Run a local AI review against scripts/sample.diff (no GitHub required)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dotenv import load_dotenv

from review import format_summary_comment, review_with_gpt4o
REPO_ROOT = SCRIPTS_DIR.parent


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set. Add it to .env in the repo root.", file=sys.stderr)
        sys.exit(1)

    diff_path = SCRIPTS_DIR / "sample.diff"
    diff = diff_path.read_text(encoding="utf-8")

    print(f"Loaded diff from {diff_path} ({len(diff)} chars)\n", file=sys.stderr)
    print("Requesting review from GPT-4o...\n", file=sys.stderr)

    review = review_with_gpt4o(api_key, diff)

    print("=== Review JSON ===\n")
    print(json.dumps(review, indent=2, ensure_ascii=False))

    print("\n=== Formatted PR comment ===\n")
    print(format_summary_comment(review))


if __name__ == "__main__":
    main()
