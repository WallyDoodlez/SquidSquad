#!/usr/bin/env python3
"""G2→3 gate verification for #6274 (per DS F1 resolution).

The original G2→3 gate ("zero new role:dev/role:qa labels in 7d")
was unsatisfiable because D3 keeps the dual-labeling code emitting
both labels through the entire 30-day window — that's the intended
behavior. Per F1's resolution, the corrected gate verifies the
*inverse*: every issue created in the trailing N days must carry
BOTH the old and the new role label, proving dual-labeling has
been working correctly up to the cutover moment.

Usage:
    python references/scripts/verify_dual_label_6274.py            # 7-day window (default)
    python references/scripts/verify_dual_label_6274.py --days 14  # custom window

Exit codes:
    0 — every issue in the window carries both labels (gate passes)
    1 — at least one issue is single-labeled (gate fails); offenders printed

Lifecycle: lands in the sub-phase 6274.1 PR for symmetry with
`migrate_labels_6274.py`, but the gate check itself only runs during
the G2→3 verification before 6274.3 ships.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys


PAIRS = [
    ("role:dev", "role:worker"),
    ("role:qa", "role:verifier"),
]


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )


def _list_recent_issues(since_iso: str) -> list[dict]:
    """List all issues created since `since_iso` (YYYY-MM-DD).

    `gh issue list --search created:>=YYYY-MM-DD` returns matches across
    open and closed states. We include both because dual-labeling
    correctness is independent of issue state.
    """
    result = _run([
        "gh", "issue", "list",
        "--state", "all",
        "--search", f"created:>={since_iso}",
        "--limit", "500",
        "--json", "number,labels,title,createdAt,state",
    ])
    if result.returncode != 0:
        print(
            f"ERROR: gh issue list failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError as e:
        print(
            f"ERROR: could not parse gh issue list output: {e}",
            file=sys.stderr,
        )
        sys.exit(2)


def verify(days: int = 7) -> dict:
    """Walk issues from the trailing window and assert dual-labeling.

    Returns a summary dict. The CLI prints it as JSON and uses the
    `passed` field to decide the exit code.
    """
    since = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    ).strftime("%Y-%m-%d")
    issues = _list_recent_issues(since)

    offenders: list[dict] = []
    checked = 0
    for issue in issues:
        labels = {entry.get("name", "") for entry in issue.get("labels", [])}
        # Only check issues that carry one of the role:* pairs at all.
        # Issues with neither (e.g. type:task with no role label, or
        # external triage-pending issues) are out of scope for this gate.
        for old_label, new_label in PAIRS:
            has_old = old_label in labels
            has_new = new_label in labels
            if not (has_old or has_new):
                continue
            checked += 1
            if not (has_old and has_new):
                offenders.append({
                    "number": issue.get("number"),
                    "title": (issue.get("title") or "")[:80],
                    "missing": new_label if has_old else old_label,
                    "labels_present": sorted(labels),
                    "createdAt": issue.get("createdAt"),
                })

    return {
        "window_days": days,
        "since_utc_date": since,
        "issues_with_role_label_checked": checked,
        "offenders": offenders,
        "passed": len(offenders) == 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "G2→3 gate verification for #6274. Asserts that every issue "
            "created in the trailing window carries BOTH the old and "
            "new role:* labels (proving dual-labeling functioned)."
        )
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Trailing window in days (default: 7).",
    )
    args = parser.parse_args(argv)

    summary = verify(days=args.days)
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
