#!/usr/bin/env python3
"""TC coverage gate — verify all TEST-PLAN TCs are accounted for in QA-RESULTS.

Exit codes:
    0 — 100% coverage, no BLOCKED results (or no test plan found / 0 TCs)
    1 — coverage gap, invalid results, duplicates, or other errors
    2 — 100% coverage but BLOCKED results exist (cannot ship)

Usage:
    python tc_coverage.py --test-plan PATH --qa-results PATH
    python tc_coverage.py --issue NUMBER
    python tc_coverage.py --help
"""

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"

# --- TC ID parsing ---

# Heading pattern: ### TC-1: or ### TC-01: or ### TC 01: (must be at heading position)
_TC_HEADING_RE = re.compile(
    r"^#{1,6}\s+TC[\s\-]?(\d+)\s*:", re.IGNORECASE
)

# Table row pattern: | TC-1 | RESULT | ... | (TC at start of a table cell)
_TC_TABLE_RE = re.compile(
    r"^\|\s*TC[\s\-]?(\d+)\s*\|", re.IGNORECASE
)

# Valid result tokens (case-insensitive matching)
_VALID_RESULTS = {"PASS", "FAIL", "BLOCKED"}

# Invalid result tokens to explicitly reject
_INVALID_RESULTS_RE = re.compile(
    r"\b(not[\s\-]?applicable|n/?a|deferred)\b", re.IGNORECASE
)

# Result extraction from heading line or next few lines
_RESULT_RE = re.compile(
    r"\b(PASS|FAIL|BLOCKED|HUMAN[\s\-]?REQUIRED)\b", re.IGNORECASE
)


def _normalize_tc_id(raw_num: str) -> int:
    """Normalize a TC number string to an integer (strips zero-padding)."""
    return int(raw_num)


def parse_tc_ids(text: str) -> list[int]:
    """Extract TC IDs from a markdown file in heading or table-row position.

    Returns a list of TC IDs (as ints). May contain duplicates.
    """
    ids = []
    for line in text.splitlines():
        m = _TC_HEADING_RE.match(line) or _TC_TABLE_RE.match(line)
        if m:
            ids.append(_normalize_tc_id(m.group(1)))
    return ids


def parse_tc_results(text: str) -> dict[int, str]:
    """Extract TC IDs and their results from a QA-RESULTS markdown file.

    Returns {tc_id: result_string}. result_string is uppercased.
    Detects invalid results (not-applicable, deferred, N/A).
    """
    results = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        is_table = _TC_TABLE_RE.match(line)
        m = _TC_HEADING_RE.match(line) or is_table
        if not m:
            continue
        tc_id = _normalize_tc_id(m.group(1))

        # For table rows, result is on the same line (| TC-1 | PASS |).
        # For headings, skip the heading line to avoid matching words in
        # the TC title like "not-applicable" (#2469). Stop at the next
        # TC marker to avoid bleeding into adjacent TCs.
        start = i if is_table else i + 1
        result_lines = []
        for j in range(start, min(i + 5, len(lines))):
            if j != i and (_TC_HEADING_RE.match(lines[j]) or _TC_TABLE_RE.match(lines[j])):
                break
            result_lines.append(lines[j])
        search_block = "\n".join(result_lines)

        # Check for invalid results first
        if _INVALID_RESULTS_RE.search(search_block):
            results[tc_id] = "INVALID"
            continue

        # Look for valid result
        rm = _RESULT_RE.search(search_block)
        if rm:
            result = rm.group(1).upper().replace(" ", "-").replace("\t", "-")
            if result.startswith("HUMAN"):
                result = "HUMAN-REQUIRED"
            results[tc_id] = result
        else:
            # TC present but no recognizable result
            results[tc_id] = "UNKNOWN"

    return results


# --- Auto-discovery ---


def _discover_files(issue_number: int) -> tuple[Path | None, Path | None]:
    """Auto-discover TEST-PLAN and QA-RESULTS files for an issue number.

    Searches .squidsquad/*/planning/ directories.
    PM planning dir is preferred over other roles.
    For QA-RESULTS, picks highest -RN revision.
    """
    planning_dirs = sorted(SQUID_DIR.glob("*/planning"))

    # Sort to put pm first (PM owns test plans)
    planning_dirs = sorted(
        planning_dirs, key=lambda p: (0 if p.parent.name == "pm" else 1, p.parent.name)
    )

    test_plan = None
    qa_results = None

    for pdir in planning_dirs:
        # Find TEST-PLAN
        if test_plan is None:
            matches = list(pdir.glob(f"*-{issue_number}-TEST-PLAN.md"))
            if matches:
                test_plan = matches[0]

        # Find QA-RESULTS (prefer highest -RN revision)
        if qa_results is None:
            base_matches = list(pdir.glob(f"*-{issue_number}-QA-RESULTS.md"))
            rev_matches = list(pdir.glob(f"*-{issue_number}-QA-RESULTS-R*.md"))

            if rev_matches:
                # Sort by revision number, pick highest
                def _rev_num(p):
                    m = re.search(r"-R(\d+)\.md$", p.name)
                    return int(m.group(1)) if m else 0

                rev_matches.sort(key=_rev_num)
                qa_results = rev_matches[-1]
            elif base_matches:
                qa_results = base_matches[0]

    return test_plan, qa_results


# --- Main logic ---


def check_coverage(
    test_plan_path: str,
    qa_results_path: str,
    debug: bool = False,
) -> int:
    """Check TC coverage between a TEST-PLAN and QA-RESULTS file.

    Returns exit code: 0 (pass), 1 (fail), 2 (blocked).
    """
    plan_text = Path(test_plan_path).read_text(encoding="utf-8")
    results_text = Path(qa_results_path).read_text(encoding="utf-8")

    plan_ids = parse_tc_ids(plan_text)
    result_map = parse_tc_results(results_text)

    # Check for duplicates in TEST-PLAN
    seen = set()
    duplicates = []
    for tc_id in plan_ids:
        if tc_id in seen:
            duplicates.append(tc_id)
        seen.add(tc_id)

    if duplicates:
        dup_strs = [f"TC-{d}" for d in sorted(set(duplicates))]
        print(
            f"ERROR: Duplicate TC IDs in TEST-PLAN: {', '.join(dup_strs)}",
            file=sys.stderr,
        )
        return 1

    plan_set = set(plan_ids)
    results_set = set(result_map.keys())

    # Handle empty plan
    if not plan_set:
        print("No TCs found in TEST-PLAN. Gate skipped (0/0).")
        return 0

    # Check for missing TCs
    missing = plan_set - results_set
    extra = results_set - plan_set

    # Check for invalid results
    invalid = {
        tc_id: result
        for tc_id, result in result_map.items()
        if tc_id in plan_set and result == "INVALID"
    }

    # Check for BLOCKED results
    blocked = {
        tc_id
        for tc_id, result in result_map.items()
        if tc_id in plan_set and result == "BLOCKED"
    }

    covered = plan_set - missing
    coverage_pct = (len(covered) / len(plan_set) * 100) if plan_set else 100

    # Print report
    print(f"TC Coverage: {len(covered)}/{len(plan_set)} ({coverage_pct:.0f}%)")

    if debug:
        # Print unmatched lines from QA-RESULTS
        print("\n--- Debug: unmatched lines in QA-RESULTS ---", file=sys.stderr)
        for i, line in enumerate(results_text.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            m = _TC_HEADING_RE.match(line) or _TC_TABLE_RE.match(line)
            if not m:
                print(f"  L{i}: {line}", file=sys.stderr)

    errors = False

    if missing:
        missing_strs = [f"TC-{m}" for m in sorted(missing)]
        print(f"Missing TCs: {', '.join(missing_strs)}", file=sys.stderr)
        errors = True

    if invalid:
        for tc_id in sorted(invalid):
            print(
                f"Invalid result for TC-{tc_id}: only PASS, FAIL, BLOCKED are valid",
                file=sys.stderr,
            )
        errors = True

    if extra:
        extra_strs = [f"TC-{e}" for e in sorted(extra)]
        print(f"Extra TCs in QA-RESULTS not in TEST-PLAN: {', '.join(extra_strs)}", file=sys.stderr)
        errors = True

    if errors:
        return 1

    if blocked:
        blocked_strs = [f"TC-{b}" for b in sorted(blocked)]
        print(f"BLOCKED TCs: {', '.join(blocked_strs)} — cannot ship", file=sys.stderr)
        return 2

    print("All TCs accounted for. Gate passed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="TC coverage gate — verify TEST-PLAN TCs are covered in QA-RESULTS"
    )
    parser.add_argument("--test-plan", help="Path to TEST-PLAN.md")
    parser.add_argument("--qa-results", help="Path to QA-RESULTS.md")
    parser.add_argument("--issue", type=int, help="Issue number for auto-discovery")
    parser.add_argument("--debug", action="store_true", help="Print unmatched lines")

    args = parser.parse_args()

    if args.test_plan and args.qa_results:
        test_plan_path = args.test_plan
        qa_results_path = args.qa_results
    elif args.issue:
        tp, qr = _discover_files(args.issue)
        if tp is None:
            print(f"No test plan found for issue #{args.issue}. Gate skipped.")
            return 0
        if qr is None:
            print(
                f"Test plan found but no QA-RESULTS for issue #{args.issue}.",
                file=sys.stderr,
            )
            return 1
        test_plan_path = str(tp)
        qa_results_path = str(qr)
        print(f"Discovered: {tp.name} / {qr.name}")
    else:
        parser.print_help()
        return 1

    return check_coverage(test_plan_path, qa_results_path, debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
