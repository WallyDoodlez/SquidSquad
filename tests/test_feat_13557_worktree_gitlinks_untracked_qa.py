"""#13557: .claude/worktrees/* gitlinks must stay untracked and gitignored.

QA-authored regression test (verifier-promoted). The fix (commit 1482437da)
untracked 4 stale worktree gitlinks and added `.claude/worktrees/` to
.gitignore. The issue explicitly flagged checking whether the sibling #4829
static gate (tests/test_git_ops.py::TestGitignoreVolatileFiles) extends to
this class; it does not, so this test closes that gap directly rather than
widening the shared VOLATILE_PATTERNS list (worktrees are machine-local
gitlinks, a distinct category from the tracked-volatile-file class there).
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_no_worktree_gitlinks_tracked():
    result = subprocess.run(
        ["git", "ls-files", ".claude/worktrees/"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    assert result.stdout.strip() == "", (
        f".claude/worktrees/ has tracked entries (should be none): "
        f"{result.stdout.strip()!r}"
    )


def test_gitignore_covers_worktrees_dir():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".claude/worktrees/" in gitignore, (
        ".gitignore is missing the .claude/worktrees/ pattern"
    )


def test_new_worktree_file_is_ignored():
    """Live probe: a fresh file under .claude/worktrees/ must be git-ignored,
    not merely absent — this is what prevents the class from recurring via a
    broad `git add -A`."""
    probe_dir = REPO_ROOT / ".claude" / "worktrees"
    probe_dir.mkdir(parents=True, exist_ok=True)
    probe = probe_dir / "test-probe-13557-regression"
    probe.write_text("probe")
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(probe.relative_to(REPO_ROOT))],
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            "a new file under .claude/worktrees/ is NOT git-ignored"
        )
    finally:
        probe.unlink()
