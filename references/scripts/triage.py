#!/usr/bin/env python3
"""Deterministic triage for QA-rejected in-progress items (#470).

Replaces prose-dependent comment scanning with a script that agents call
at cycle start.  Returns structured JSON so the agent knows exactly which
items need rework and what the QA feedback says.

Usage:
    python references/scripts/triage.py qa-rejected <role>
        List in-progress items for <role> that have unaddressed QA/PM feedback.

    python references/scripts/triage.py qa-rejected <role> --json
        Same, but output as JSON array.

Exit codes:
    0 — items found (print them)
    0 — no items found (empty output / empty JSON array)
    1 — error (gh CLI failure, etc.)
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Roles whose comments count as "QA feedback" that needs rework
# #6274 dual-aware: "verifier" is the new canonical for the qa role; both names
# are accepted during the 30-day window (post-6274.3 cutover, "qa" is removed
# and this collapses to {"pm", "verifier"}).
QA_FEEDBACK_ROLES = {"pm", "qa", "verifier"}


def _parse_timestamp(ts):
    """Parse a GitHub ISO 8601 timestamp to a datetime for safe comparison.

    Handles both 'Z' suffix and '+00:00' offset formats.
    Returns None if parsing fails.
    """
    if not ts:
        return None
    try:
        # Python 3.11+ fromisoformat handles 'Z' directly
        return datetime.fromisoformat(ts)
    except ValueError:
        pass
    # Fallback: strip Z and parse as naive UTC
    try:
        return datetime.strptime(ts.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError):
        return None


def _gh(*args: str) -> str:
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh command failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _parse_comment_role(body: str) -> str | None:
    """Extract the role name from a comment body like '**skill-lead**: ...'

    Returns the base role (e.g. 'pm' from '**pm (pm)**:', 'skill' from
    '**skill-lead**:').  Returns None if no role prefix found.
    """
    if not body.startswith("**"):
        return None
    end = body.find("**", 2)
    if end == -1:
        return None
    role_str = body[2:end].strip()
    # Strip alias parenthetical: "pm (pm)" -> "pm"
    if "(" in role_str:
        role_str = role_str[: role_str.index("(")].strip()
    # Strip "-lead" suffix: "skill-lead" -> "skill"
    if role_str.endswith("-lead"):
        role_str = role_str[: -len("-lead")]
    return role_str.lower()


def find_qa_rejected(role: str) -> list[dict]:
    """Find in-progress items for `role` with unaddressed QA/PM feedback.

    An item is "QA-rejected" if:
    1. It has status:in-progress and role:<role> labels
    2. The most recent QA/PM comment is newer than the most recent
       <role>-lead comment (i.e. feedback hasn't been addressed yet)

    Returns a list of dicts: {number, title, feedback_from, feedback_at,
    feedback_summary}.
    """
    # Get in-progress items for this role
    raw = _gh(
        "issue", "list",
        "--label", f"status:in-progress",
        "--label", f"role:{role}",
        "--state", "open",
        "--json", "number,title",
        "--limit", "50",
    )
    try:
        items = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []
    if not items:
        return []

    results = []
    for item in items:
        number = item["number"]
        # Fetch comments — isolate per-issue failures so one bad issue
        # doesn't abort the entire triage scan (#4051).
        try:
            detail_raw = _gh(
                "issue", "view", str(number),
                "--json", "comments",
            )
        except RuntimeError:
            continue
        try:
            detail = json.loads(detail_raw)
        except json.JSONDecodeError:
            continue
        comments = detail.get("comments", [])
        if not comments:
            continue

        # Find the latest comment from the agent's own role
        last_own_at = None
        for c in comments:
            cr = _parse_comment_role(c["body"])
            if cr and cr == role:
                last_own_at = c["createdAt"]

        # Find the latest QA/PM feedback comment
        last_feedback = None
        for c in comments:
            cr = _parse_comment_role(c["body"])
            if cr and cr in QA_FEEDBACK_ROLES:
                last_feedback = c

        if not last_feedback:
            continue

        # Check if feedback is newer than our last comment
        feedback_at = last_feedback["createdAt"]
        feedback_dt = _parse_timestamp(feedback_at)
        own_dt = _parse_timestamp(last_own_at)
        if own_dt and feedback_dt and feedback_dt <= own_dt:
            continue  # We already responded

        # Extract a summary (first 200 chars of the feedback body)
        body = last_feedback["body"]
        # Strip the role prefix
        colon_idx = body.find(":")
        summary = body[colon_idx + 1:].strip() if colon_idx != -1 else body
        if len(summary) > 200:
            summary = summary[:197] + "..."

        feedback_role = _parse_comment_role(last_feedback["body"]) or "unknown"

        results.append({
            "number": number,
            "title": item["title"],
            "feedback_from": feedback_role,
            "feedback_at": feedback_at,
            "feedback_summary": summary,
        })

    return results


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "qa-rejected":
        print("Usage: triage.py qa-rejected <role> [--json]", file=sys.stderr)
        sys.exit(1)

    role = sys.argv[2]
    as_json = "--json" in sys.argv

    try:
        items = find_qa_rejected(role)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(json.dumps(items, indent=2))
    else:
        if not items:
            return
        for item in items:
            print(
                f"#{item['number']}: {item['title']} "
                f"(feedback from {item['feedback_from']} at {item['feedback_at']})"
            )
            print(f"  {item['feedback_summary']}")


if __name__ == "__main__":
    main()
