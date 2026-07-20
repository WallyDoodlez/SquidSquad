"""#13714 — harness runtime log files must never enter git.

commit_state()'s sweep (references/scripts/git_ops.py) stages every
untracked/modified path under .squidsquad/ reported by `git status
--porcelain`. Live, continuously-growing harness logs (harness-errors.log,
harness-supervisor.log, harness-supervisor.log.err) got swept into a state
commit on main because nothing ignored them. Fixed via .gitignore entries —
git-ignored paths never show up in `git status --porcelain`, so the sweep
excludes them automatically with no code change needed.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

HARNESS_LOG_NAMES = [
    "harness-errors.log",
    "harness-supervisor.log",
    "harness-supervisor.log.err",
]


class TestHarnessLogsGitignored:
    def test_gitignore_lists_all_three_log_names(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for name in HARNESS_LOG_NAMES:
            assert f".squidsquad/{name}" in gitignore, (
                f".gitignore is missing an entry for {name}")

    def test_git_actually_ignores_each_log_path(self):
        for name in HARNESS_LOG_NAMES:
            probe = REPO_ROOT / ".squidsquad" / name
            pre_existing = probe.exists()
            if not pre_existing:
                probe.write_text("probe", encoding="utf-8")
            try:
                result = subprocess.run(
                    ["git", "check-ignore", "-q", f".squidsquad/{name}"],
                    cwd=str(REPO_ROOT),
                )
                assert result.returncode == 0, (
                    f".squidsquad/{name} is NOT git-ignored")
            finally:
                if not pre_existing:
                    probe.unlink()

    def test_untracked_harness_log_absent_from_status_porcelain(self):
        """The actual failure mode from #13714: a live untracked log file
        must not appear in `git status --porcelain` (what commit_state's
        sweep reads), even though the file physically exists on disk."""
        probe = REPO_ROOT / ".squidsquad" / "harness-errors.log"
        pre_existing = probe.exists()
        if not pre_existing:
            probe.write_text("simulated harness log line\n", encoding="utf-8")
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", ".squidsquad/harness-errors.log"],
                cwd=str(REPO_ROOT), capture_output=True, text=True,
            )
            assert result.stdout.strip() == "", (
                "an ignored harness log still shows up in git status --porcelain "
                f"(would be swept by commit_state): {result.stdout!r}")
        finally:
            if not pre_existing:
                probe.unlink()
