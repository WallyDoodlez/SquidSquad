"""#14024 -- task_end's uncommitted-changes warning must classify lanes.

The warning fired on raw ``git status --porcelain`` with no _is_state_file
classification, so state-lane artifacts that by DESIGN never ride the
feature branch (working-state.md, planning CODE-REVIEW files, .claude/ live
copies) triggered it every time -- 4/4 false positives per session on
2026-07-20 -- and the advice ("commit via commit-code") was actively wrong
for them. Contract now pinned: code-dirty -> warning naming the code paths;
state-only-dirty -> a distinct commit-state note, no commit-code warning;
mixed -> warning names ONLY the code paths.
"""

import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import git_ops  # noqa: E402


class TestClassifyPorcelain:
    def test_split_by_lane(self):
        out = (
            " M references/scripts/foo.py\n"
            "?? tests/test_foo.py\n"
            " M .squidsquad/skill/working-state.md\n"
            "?? .claude/skills/vault-search/SKILL.md\n"
        )
        code, state = git_ops._classify_porcelain(out)
        assert code == ["references/scripts/foo.py", "tests/test_foo.py"]
        assert state == [".squidsquad/skill/working-state.md",
                         ".claude/skills/vault-search/SKILL.md"]

    def test_rename_resolves_to_new_name(self):
        out = "R  old/name.py -> references/scripts/new_name.py\n"
        code, state = git_ops._classify_porcelain(out)
        assert code == ["references/scripts/new_name.py"]

    def test_quoted_path_unquoted(self):
        out = '?? "references/scripts/spaced name.py"\n'
        code, _ = git_ops._classify_porcelain(out)
        assert code == ["references/scripts/spaced name.py"]

    def test_launcher_scripts_are_code(self):
        out = " M .squidsquad/start.ps1\n"
        code, state = git_ops._classify_porcelain(out)
        assert code == [".squidsquad/start.ps1"]
        assert state == []

    def test_blank_lines_skipped(self):
        code, state = git_ops._classify_porcelain("\n \n")
        assert code == [] and state == []


class TestTaskEndWarning:
    """Drive task_end with stubbed git plumbing and capture stderr."""

    def _run_task_end(self, monkeypatch, porcelain):
        def fake_run(cmd, check=True, **kw):
            r = types.SimpleNamespace(returncode=0, stdout="", stderr="")
            if "status --porcelain" in cmd:
                r.stdout = porcelain
            return r

        monkeypatch.setattr(git_ops, "_run", fake_run)
        monkeypatch.setattr(git_ops, "_run_list",
                            lambda cmd, check=True, **kw: types.SimpleNamespace(
                                returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(git_ops, "_get_working_branch", lambda: "main")
        monkeypatch.setattr(git_ops, "_safe_checkout", lambda b: True)
        monkeypatch.setattr(git_ops, "_emit", lambda *a, **kw: None)
        git_ops.task_end("skill", 14024)

    def test_code_dirty_warns_naming_code_paths(self, monkeypatch, capsys):
        self._run_task_end(monkeypatch,
                           " M references/scripts/foo.py\n"
                           " M .squidsquad/skill/working-state.md\n")
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "references/scripts/foo.py" in err
        assert "commit-code" in err
        # Mixed case: the state path must NOT be named in the warning.
        assert "working-state.md" not in err

    def test_state_only_no_commit_code_warning(self, monkeypatch, capsys):
        self._run_task_end(monkeypatch,
                           " M .squidsquad/skill/working-state.md\n"
                           "?? .squidsquad/pm/planning/CODE-REVIEW-1.md\n"
                           "?? .claude/skills/vault-search/SKILL.md\n")
        err = capsys.readouterr().err
        assert "WARNING" not in err
        assert "commit-state" in err

    def test_clean_tree_silent(self, monkeypatch, capsys):
        self._run_task_end(monkeypatch, "")
        err = capsys.readouterr().err
        assert "WARNING" not in err
        assert "commit-state" not in err

    def test_launcher_dirt_still_warns(self, monkeypatch, capsys):
        """Launcher scripts are code-lane despite the .squidsquad/ prefix."""
        self._run_task_end(monkeypatch, " M .squidsquad/start.sh\n")
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert ".squidsquad/start.sh" in err
