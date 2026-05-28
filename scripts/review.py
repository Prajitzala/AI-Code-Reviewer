#!/usr/bin/env python3
"""AI-powered PR code review for GitHub Actions."""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request

MODEL = "__MODEL__"
try:
    MAX_DIFF_CHARS = __MAX_DIFF_CHARS__  # noqa: F821 — replaced on scaffold
except NameError:
    MAX_DIFF_CHARS = 120_000

GITHUB_API = "https://api.github.com"
OPENAI_API = "https://api.openai.com/v1/chat/completions"

SKIP_SUFFIXES = (
    ".lock",
    ".png",
    ".jpg",
    ".svg",
    ".min.js",
    ".min.css",
    ".map",
)
SKIP_FILENAMES = frozenset(
    {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
)

SYSTEM_PROMPT = """You are an expert code reviewer. Return a JSON object with:
- summary: 2-3 sentence overall assessment
- verdict: APPROVE | REQUEST_CHANGES | COMMENT
- issues: array of { severity, category, title, description, path, line }
  severity: critical | warning | suggestion
  category: bug | security | performance | quality
- positives: array of strings (things done well)
- inline_comments: array of { path, line, body } — one entry per issue with a file path and line (use diff line numbers)
Return ONLY valid JSON."""

HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "⚠️",
    "suggestion": "💡",
}
VERDICT_BADGE = {
    "APPROVE": "✅ APPROVE",
    "REQUEST_CHANGES": "❌ REQUEST CHANGES",
    "COMMENT": "💬 COMMENT",
}
SEVERITY_ORDER = ("critical", "warning", "suggestion")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def should_skip_file(filename: str) -> bool:
    base = os.path.basename(filename)
    if base in SKIP_FILENAMES:
        return True
    return filename.endswith(SKIP_SUFFIXES)


def github_request(
    method: str,
    path: str,
    token: str,
    data: dict | None = None,
) -> tuple[int, dict | list | None]:
    url = f"{GITHUB_API}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-code-reviewer",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = {"message": raw}
        return exc.code, payload


def fetch_pr_files(repo: str, pr_number: str, token: str) -> list[dict]:
    files: list[dict] = []
    page = 1
    while True:
        path = f"/repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}"
        status, payload = github_request("GET", path, token)
        if status != 200 or not isinstance(payload, list):
            raise RuntimeError(
                f"Failed to fetch PR files (HTTP {status}): {payload}"
            )
        if not payload:
            break
        files.extend(payload)
        if len(payload) < 100:
            break
        page += 1
    return files


def build_diff_string(files: list[dict]) -> str:
    parts: list[str] = []
    for entry in files:
        filename = entry.get("filename") or ""
        if should_skip_file(filename):
            continue
        patch = entry.get("patch")
        if not patch:
            continue
        parts.append(f"--- {filename}\n{patch}")
    diff = "\n\n".join(parts)
    if len(diff) > MAX_DIFF_CHARS:
        truncated = diff[:MAX_DIFF_CHARS]
        diff = (
            f"{truncated}\n\n"
            f"[Diff truncated at {MAX_DIFF_CHARS} characters]"
        )
    return diff


def commentable_lines_in_patch(patch: str) -> set[int]:
    """Line numbers on the RIGHT (new) side that accept review comments."""
    valid: set[int] = set()
    new_line = 0
    in_hunk = False
    for raw in patch.splitlines():
        if raw.startswith("@@"):
            match = HUNK_RE.search(raw)
            if match:
                new_line = int(match.group(1))
                in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+") and not raw.startswith("++"):
            valid.add(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("--"):
            continue
        else:
            valid.add(new_line)
            new_line += 1
    return valid


def resolve_inline_line(patch: str | None, line: int) -> int | None:
    if not patch:
        return None
    valid = commentable_lines_in_patch(patch)
    if not valid:
        return None
    if line in valid:
        return line
    return min(valid, key=lambda candidate: abs(candidate - line))


def build_patch_map(files: list[dict]) -> dict[str, str | None]:
    return {
        entry["filename"]: entry.get("patch")
        for entry in files
        if entry.get("filename")
    }


def collect_inline_comments(
    review: dict,
    files: list[dict],
) -> list[dict]:
    """Merge model inline_comments with issues; snap lines to the PR diff."""
    patch_map = build_patch_map(files)
    seen: set[tuple[str, int]] = set()
    collected: list[dict] = []

    def add(path: str | None, line: object, body: str | None) -> None:
        if not path or not body or line is None:
            return
        try:
            requested = int(line)
        except (TypeError, ValueError):
            return
        resolved = resolve_inline_line(patch_map.get(path), requested)
        if resolved is None:
            log(
                f"Skipping inline comment on {path}:{requested} "
                "(line not in PR diff)"
            )
            return
        key = (path, resolved)
        if key in seen:
            return
        seen.add(key)
        collected.append({"path": path, "line": resolved, "body": body})

    for item in review.get("inline_comments") or []:
        add(item.get("path"), item.get("line"), item.get("body"))

    for issue in review.get("issues") or []:
        title = issue.get("title") or "Issue"
        description = issue.get("description") or ""
        body = f"**{title}**\n\n{description}" if description else title
        add(issue.get("path"), issue.get("line"), body)

    return collected


def review_with_gpt4o(
    api_key: str,
    diff: str,
    repo: str = "local/test",
    pr_number: str = "0",
) -> dict:
    """Send a diff to GPT-4o and return the parsed review JSON."""
    return _request_openai_review(api_key, diff, repo, pr_number, "gpt-4o")


def _request_openai_review(
    api_key: str,
    diff: str,
    repo: str,
    pr_number: str,
    model: str,
) -> dict:
    user_content = (
        f"Repository: {repo}\n"
        f"Pull request: #{pr_number}\n"
        f"Base SHA: {os.environ.get('BASE_SHA', '')}\n"
        f"Head SHA: {os.environ.get('HEAD_SHA', '')}\n\n"
        f"Diff:\n{diff}"
    )
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        OPENAI_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    content = result["choices"][0]["message"]["content"]
    return json.loads(content)


def format_summary_comment(review: dict) -> str:
    verdict = (review.get("verdict") or "COMMENT").upper()
    badge = VERDICT_BADGE.get(verdict, f"💬 {verdict}")
    lines = [
        "## 🤖 AI Code Review",
        "",
        f"**Verdict:** {badge}",
        "",
        "### Summary",
        review.get("summary") or "_No summary provided._",
        "",
    ]

    issues = review.get("issues") or []
    by_severity: dict[str, list[dict]] = {s: [] for s in SEVERITY_ORDER}
    for issue in issues:
        sev = (issue.get("severity") or "suggestion").lower()
        if sev not in by_severity:
            by_severity[sev] = []
        by_severity[sev].append(issue)

    severity_titles = {
        "critical": "Critical",
        "warning": "Warnings",
        "suggestion": "Suggestions",
    }
    for sev in SEVERITY_ORDER:
        group = by_severity.get(sev) or []
        if not group:
            continue
        emoji = SEVERITY_EMOJI.get(sev, "•")
        lines.append(f"### {emoji} {severity_titles[sev]}")
        lines.append("")
        for issue in group:
            title = issue.get("title") or "Issue"
            path = issue.get("path") or ""
            line = issue.get("line")
            category = issue.get("category") or ""
            loc = f"`{path}`" if path else ""
            if line:
                loc = f"`{path}:{line}`" if path else f"line {line}"
            cat = f" ({category})" if category else ""
            lines.append(f"- **{title}**{cat} — {loc}")
            desc = issue.get("description")
            if desc:
                lines.append(f"  {desc}")
        lines.append("")

    positives = review.get("positives") or []
    if positives:
        lines.append("### ✨ Positives")
        lines.append("")
        for item in positives:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("---")
    lines.append("*Reviewed by @prajitzala/ai-code-reviewer*")
    return "\n".join(lines)


def post_pr_comment(repo: str, pr_number: str, token: str, body: str) -> None:
    path = f"/repos/{repo}/issues/{pr_number}/comments"
    status, payload = github_request("POST", path, token, {"body": body})
    if status not in (200, 201):
        raise RuntimeError(f"Failed to post PR comment (HTTP {status}): {payload}")


def post_inline_comments(
    repo: str,
    pr_number: str,
    token: str,
    head_sha: str,
    inline_comments: list[dict],
) -> None:
    """Post line-level comments on the PR diff (422-safe, per comment)."""
    if not inline_comments or not head_sha:
        return

    comment_path = f"/repos/{repo}/pulls/{pr_number}/comments"
    posted = 0

    for item in inline_comments:
        payload = {
            "body": item["body"],
            "commit_id": head_sha,
            "path": item["path"],
            "line": item["line"],
            "side": "RIGHT",
        }
        status, response = github_request("POST", comment_path, token, payload)
        if status in (200, 201):
            posted += 1
            continue
        if status == 422:
            log(
                f"Inline comment skipped for {item['path']}:{item['line']} "
                f"(422): {response}"
            )
            continue
        log(
            f"Inline comment failed for {item['path']}:{item['line']} "
            f"(HTTP {status}): {response}"
        )

    log(f"Posted {posted}/{len(inline_comments)} inline comment(s)")


def run() -> None:
    api_key = os.environ["OPENAI_API_KEY"]
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    head_sha = os.environ.get("HEAD_SHA", "")

    log(f"Fetching changed files for {repo}#{pr_number}...")
    files = fetch_pr_files(repo, pr_number, token)
    diff = build_diff_string(files)
    if not diff.strip():
        log("No reviewable diff content; skipping OpenAI call")
        post_pr_comment(
            repo,
            pr_number,
            token,
            "## 🤖 AI Code Review\n\n"
            "No reviewable code changes found "
            "(all files were skipped or had no patch).\n\n"
            "---\n"
            "*Reviewed by @prajitzala/ai-code-reviewer*",
        )
        return

    model = MODEL if MODEL != "__MODEL__" else "gpt-4o"
    log(f"Requesting review from {model} ({len(diff)} chars)...")
    review = _request_openai_review(api_key, diff, repo, pr_number, model)

    summary_comment = format_summary_comment(review)
    log("Posting summary comment...")
    post_pr_comment(repo, pr_number, token, summary_comment)

    inline = collect_inline_comments(review, files)
    if inline and head_sha:
        log(f"Posting {len(inline)} inline comment(s)...")
        post_inline_comments(repo, pr_number, token, head_sha, inline)
    elif inline and not head_sha:
        log("HEAD_SHA not set; skipping inline comments")


def main() -> None:
    try:
        run()
    except Exception:
        log("Review failed (non-blocking):")
        log(traceback.format_exc())
    sys.exit(0)


if __name__ == "__main__":
    if not __package__:
        from pathlib import Path

        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    main()
