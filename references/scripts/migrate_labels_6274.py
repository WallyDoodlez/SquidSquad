#!/usr/bin/env python3
"""One-shot label migration for #6274.

Walks every OPEN issue/task tagged `role:dev` or `role:qa` and adds the
matching new-prefix label (`role:worker` or `role:verifier`) alongside.
Idempotent: an issue that already carries both labels is skipped.

Usage:
    python references/scripts/migrate_labels_6274.py            # apply changes
    python references/scripts/migrate_labels_6274.py --dry-run  # report only

Lifecycle: lands in the sub-phase 6274.1 PR. PM (or a human operator)
runs it once after the PR merges so existing open work in the tracker
acquires the dual labels needed for the 30-day window. It does NOT
touch closed/historical issues — those are intentionally left as-is.
Deleted in 6274.3 alongside `cleanup_labels_6274.py`.

Reads issues via `gh issue list`; writes via `gh issue edit ... --add-label`.
Closed/historical issues are never touched. The script exits with code 0
on success even when zero issues needed updates (idempotent re-runs are a
no-op).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# (old label, new label) pairs. Same shape as `tracker._DUAL_LABEL_PAIRS_6274`
# but expressed as label strings rather than role prefixes — this script
# operates on the GitHub label namespace directly.
LABEL_PAIRS = [
    ("role:dev", "role:worker"),
    ("role:qa", "role:verifier"),
]


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess, capturing stdout/stderr as text. Never raises on
    non-zero — caller inspects returncode."""
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )


def _list_open_issues_with_label(label: str) -> list[dict]:
    """Return the open issues carrying `label`. Each dict has at least
    `number` and `labels` (list of {name: ...} entries)."""
    result = _run([
        "gh", "issue", "list",
        "--state", "open",
        "--label", label,
        "--limit", "500",
        "--json", "number,labels,title",
    ])
    if result.returncode != 0:
        print(
            f"ERROR: gh issue list failed for label {label!r}: "
            f"{result.stderr.strip()}",
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


def _label_names(issue: dict) -> set[str]:
    return {entry.get("name", "") for entry in issue.get("labels", [])}


def _add_label(number: int, label: str) -> bool:
    """Add `label` to issue #number. Returns True on success."""
    result = _run([
        "gh", "issue", "edit", str(number),
        "--add-label", label,
    ])
    if result.returncode != 0:
        print(
            f"ERROR: failed to add {label!r} to #{number}: "
            f"{result.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def migrate(dry_run: bool = False) -> dict:
    """Walk all open issues with old role labels, add the new label
    alongside. Returns a summary dict with counts.

    The summary is the script's main return value (printed as JSON on
    success); the same structure is returned in-process so tests can
    drive the function without subprocess.
    """
    summary = {
        "dry_run": dry_run,
        "old_label_to_pairs": [],  # list of {old, new, issues: [...], updated: N, already_dual: N}
    }
    seen_issue_numbers: set[int] = set()
    for old_label, new_label in LABEL_PAIRS:
        old_issues = _list_open_issues_with_label(old_label)
        updated: list[int] = []
        already_dual: list[int] = []
        for issue in old_issues:
            number = issue.get("number")
            if number in seen_issue_numbers:
                continue  # an issue with both labels is reported under the
                          # first pair only
            seen_issue_numbers.add(number)
            labels = _label_names(issue)
            if new_label in labels:
                already_dual.append(number)
                continue
            if dry_run:
                updated.append(number)
            else:
                if _add_label(number, new_label):
                    updated.append(number)
        summary["old_label_to_pairs"].append({
            "old": old_label,
            "new": new_label,
            "scanned": len(old_issues),
            "updated": updated,
            "already_dual": already_dual,
        })
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "One-shot dual-label migration for #6274 sub-phase 6274.1. "
            "Adds role:worker / role:verifier alongside role:dev / role:qa "
            "on all open issues. Idempotent."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report what would be changed but do not call `gh issue edit`. "
            "Use this on first run to verify the planned change set."
        ),
    )
    args = parser.parse_args(argv)

    summary = migrate(dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
