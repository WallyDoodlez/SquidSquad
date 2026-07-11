"""#13433 — INDEPENDENT verifier test plan (QA).

Bug: `git_ops.py pr-merge --help` (and other malformed number positions) consumed
the flag as the PR number, printed a false "PR #--help merged (squash)", and ran
the destructive squash-merge + post-merge scope-audit/compose — dirtying the tree
with regenerated CLAUDE.md files. Fix must validate the PR-number BEFORE any side
effect and treat -h/--help as usage.

These are BLACK-BOX subprocess tests (complementary to the worker's white-box
`pr_merge`-spy tests in tests/test_git_ops.py): they invoke the real CLI and assert
the process-level contract an operator actually experiences — exit code + output +
the absence of the false "merged" signal. No merge can fire because the number
never validates.

AC map (from the #13433 issue "Suggested fix", derived independently):
  AC1  -h/--help -> subcommand usage, exit 0, NO side effect
  AC2  non-numeric PR-number token -> clean error before any merge/compose work
  AC3  a malformed invocation NEVER prints a "merged" line (no side-effect fired)
"""
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GIT_OPS = os.path.join(REPO_ROOT, "references", "scripts", "git_ops.py")


def _run(*cli_args):
    return subprocess.run(
        [sys.executable, GIT_OPS, *cli_args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_pr_merge_help_is_usage_exit0_no_merge(flag):
    """AC1: -h/--help -> exit 0, usage printed, and NO 'merged' side-effect line."""
    r = _run("pr-merge", flag)
    combined = r.stdout + r.stderr
    assert r.returncode == 0, f"{flag} must exit 0; got {r.returncode}: {combined}"
    assert "Usage" in combined and "pr-merge" in combined
    assert "merged" not in combined.lower(), "help must not print a merged line"


@pytest.mark.parametrize("bad", ["notanumber", "--strategy", "12abc", "-5"])
def test_pr_merge_non_numeric_rejected_before_side_effect(bad):
    """AC2/AC3: a non-numeric / flag token in the number position -> non-zero exit,
    'no merge attempted', and never a false 'merged' line."""
    r = _run("pr-merge", bad)
    combined = r.stdout + r.stderr
    assert r.returncode != 0, f"{bad!r} must be rejected; got exit 0: {combined}"
    assert "no merge attempted" in combined.lower(), (
        f"{bad!r} must state no merge attempted: {combined}"
    )
    assert "merged" not in combined.lower() or "no merge" in combined.lower(), (
        f"{bad!r} must not print a false success 'merged' line: {combined}"
    )


def test_pr_merge_missing_number_is_error():
    """AC2: missing PR number -> non-zero exit, usage, no merge."""
    r = _run("pr-merge")
    combined = r.stdout + r.stderr
    assert r.returncode != 0
    assert "merged" not in combined.lower()


def test_top_level_dash_h_is_help():
    """AC1: -h at the subcommand position is recognized as help (exit 0)."""
    r = _run("-h")
    assert r.returncode == 0
