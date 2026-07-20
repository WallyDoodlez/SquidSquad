"""#14054 -- wizard-deployed .claude/skills/ must be gitignored.

install_vault_engine() materializes references/skills/ -> .claude/skills/ on
every clone that runs it; the copy is regenerable deployment output (never
committed anywhere in repo history), but nothing ignored it, so `git status`
on any installed clone permanently showed it as untracked noise -- the kind
that buries genuinely important untracked files. Same class (and fix) as the
.claude/worktrees/ entry.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestClaudeSkillsGitignored:
    def test_gitignore_carries_the_entry_as_its_own_line(self):
        lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert ".claude/skills/" in lines

    def test_git_actually_ignores_a_deployed_skill_path(self):
        result = subprocess.run(
            ["git", "check-ignore", "-q", ".claude/skills/vault-search/SKILL.md"],
            cwd=str(REPO_ROOT), capture_output=True, timeout=30,
        )
        assert result.returncode == 0, (
            ".claude/skills/ paths are not actually ignored by git")

    def test_engine_source_of_truth_stays_tracked(self):
        """The committed source under references/skills/ must NOT be caught
        by the new pattern -- only the deployed live copy is ignored."""
        result = subprocess.run(
            ["git", "check-ignore", "-q",
             "references/skills/vault-search/SKILL.md"],
            cwd=str(REPO_ROOT), capture_output=True, timeout=30,
        )
        assert result.returncode != 0, (
            "the engine SOURCE package must never be gitignored")
