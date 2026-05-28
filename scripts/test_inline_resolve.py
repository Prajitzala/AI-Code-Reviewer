#!/usr/bin/env python3
"""Unit tests for inline comment line resolution (no API keys required)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from review import (  # noqa: E402
    collect_inline_comments,
    commentable_lines_in_patch,
    resolve_inline_line,
)

SAMPLE_PATCH = """@@ -1,3 +1,4 @@
 line one
-old line
+new line
 context"""


def test_commentable_lines() -> None:
    lines = commentable_lines_in_patch(SAMPLE_PATCH)
    assert lines == {1, 2, 3}


def test_resolve_snaps_to_nearest() -> None:
    assert resolve_inline_line(SAMPLE_PATCH, 3) == 3
    assert resolve_inline_line(SAMPLE_PATCH, 99) == 3


def test_collect_from_issues() -> None:
    files = [{"filename": "src/a.py", "patch": SAMPLE_PATCH}]
    review = {
        "issues": [
            {
                "path": "src/a.py",
                "line": 2,
                "title": "Test",
                "description": "Details",
            }
        ],
        "inline_comments": [],
    }
    comments = collect_inline_comments(review, files)
    assert len(comments) == 1
    assert comments[0]["line"] in commentable_lines_in_patch(SAMPLE_PATCH)


def main() -> None:
    test_commentable_lines()
    test_resolve_snaps_to_nearest()
    test_collect_from_issues()
    print("test_inline_resolve: OK")


if __name__ == "__main__":
    main()
