"""Regression test for #13672 — l4_file_watcher.py's own module docstring
documents recompose_path() as the "public entry point for both the file-watch
handler AND the optional .git/hooks/post-commit script" (PRD-E Q-E2), but
that post-commit hook never shipped: zero callers anywhere in the repo,
confirmed via grep and by listing references/git-hooks/ (only pre-commit and
post-merge existed).

Fix: a new references/git-hooks/post-commit shell hook (mirroring
pre-commit/post-merge's shape) dispatches to a new git_ops.py subcommand,
recompose-committed-l4-files, which finds any .squidsquad/project/*.md files
touched by the just-created commit and calls l4_file_watcher.recompose_path()
for each. install_hooks() now also chmods the new hook. Fully fail-open
throughout — a post-commit hook cannot abort a commit that already happened.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "references" / "git-hooks" / "post-commit"


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestPostCommitHookFileShippedExecutable13672:
    def test_hook_file_exists(self):
        assert HOOK_FILE.exists()

    def test_hook_tracked_executable(self):
        import subprocess
        out = subprocess.run(
            ["git", "ls-files", "-s", "--", "references/git-hooks/post-commit"],
            cwd=str(git_ops.REPO_ROOT), capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        line = out.stdout.strip()
        assert line, "post-commit hook is not tracked in git"
        mode = line.split()[0]
        assert mode == "100755", (
            f"post-commit hook tracked as mode {mode}, expected 100755 "
            f"(POSIX needs the exec bit or git silently skips the hook)")

    def test_hook_dispatches_to_recompose_subcommand(self):
        text = HOOK_FILE.read_text(encoding="utf-8")
        assert "recompose-committed-l4-files" in text

    def test_hook_always_exits_zero(self):
        text = HOOK_FILE.read_text(encoding="utf-8")
        assert text.rstrip().endswith("exit 0")

    def test_hook_in_installer_manifest(self):
        manifest = REPO_ROOT / "references" / "installer-files.txt"
        lines = [l.strip() for l in manifest.read_text().splitlines()]
        assert "references/git-hooks/post-commit" in lines


class TestInstallHooksChmodsPostCommitToo13672:
    def test_install_hooks_chmods_all_three(self, tmp_path, monkeypatch):
        import os
        hook_dir = tmp_path / git_ops._HOOKS_DIR_REL
        hook_dir.mkdir(parents=True)
        (hook_dir / "pre-commit").write_text("#!/bin/sh\nexit 0\n")
        (hook_dir / "post-merge").write_text("#!/bin/sh\nexit 0\n")
        (hook_dir / "post-commit").write_text("#!/bin/sh\nexit 0\n")
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        chmodded = []
        monkeypatch.setattr(os, "chmod",
                            lambda p, m, *a, **k: chmodded.append(Path(p).name))
        with patch.object(git_ops, "_run",
                          return_value=_mock_result(stdout="\n")), \
                patch.object(git_ops, "_run_list",
                             return_value=_mock_result(returncode=0)):
            assert git_ops.install_hooks() is True
        assert set(chmodded) == {"pre-commit", "post-merge", "post-commit"}

    def test_missing_post_commit_does_not_break_activation(self, tmp_path, monkeypatch):
        """Older installs / partial checkouts without the new hook must not
        regress pre-commit activation."""
        import os
        hook_dir = tmp_path / git_ops._HOOKS_DIR_REL
        hook_dir.mkdir(parents=True)
        (hook_dir / "pre-commit").write_text("#!/bin/sh\nexit 0\n")
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(os, "chmod", lambda *a, **k: None)
        with patch.object(git_ops, "_run",
                          return_value=_mock_result(stdout="\n")), \
                patch.object(git_ops, "_run_list",
                             return_value=_mock_result(returncode=0)):
            assert git_ops.install_hooks() is True


class TestRecomposeCommittedL4Files13672:
    def test_no_l4_files_in_commit_noop(self, monkeypatch):
        monkeypatch.setattr(
            git_ops, "_run_list",
            lambda cmd, **kw: _mock_result(
                stdout="references/scripts/foo.py\nREADME.md\n"),
        )
        # Must not raise, must not import l4_file_watcher's dependencies.
        git_ops._recompose_committed_l4_files()

    def test_diff_tree_failure_is_a_noop(self, monkeypatch):
        monkeypatch.setattr(
            git_ops, "_run_list", lambda cmd, **kw: _mock_result(returncode=1))
        git_ops._recompose_committed_l4_files()  # must not raise

    def test_l4_file_dispatches_to_recompose_path(self, monkeypatch):
        monkeypatch.setattr(
            git_ops, "_run_list",
            lambda cmd, **kw: _mock_result(
                stdout=".squidsquad/project/pm.md\n"),
        )
        fake_lfw = SimpleNamespace(recompose_path=MagicMock())
        fake_cfg = SimpleNamespace(
            parse_aliases_registry=MagicMock(return_value={"pm": ("pm", None)}))
        with patch.dict(sys.modules, {
            "l4_file_watcher": fake_lfw,
            "config": fake_cfg,
            "event_bus": SimpleNamespace(emit=MagicMock()),
        }):
            git_ops._recompose_committed_l4_files()
        fake_lfw.recompose_path.assert_called_once()
        call_kwargs = fake_lfw.recompose_path.call_args.kwargs
        assert call_kwargs["registry"] == {"pm": ("pm", None)}

    def test_non_project_squidsquad_files_ignored(self, monkeypatch):
        """Only .squidsquad/project/*.md is watched -- a .squidsquad/pm/
        working-state.md change must not trigger a recompose dispatch."""
        monkeypatch.setattr(
            git_ops, "_run_list",
            lambda cmd, **kw: _mock_result(
                stdout=".squidsquad/pm/working-state.md\n"),
        )
        fake_lfw = SimpleNamespace(recompose_path=MagicMock())
        with patch.dict(sys.modules, {"l4_file_watcher": fake_lfw}):
            git_ops._recompose_committed_l4_files()
        fake_lfw.recompose_path.assert_not_called()

    def test_one_file_failure_does_not_skip_the_rest(self, monkeypatch, capsys):
        monkeypatch.setattr(
            git_ops, "_run_list",
            lambda cmd, **kw: _mock_result(
                stdout=".squidsquad/project/pm.md\n"
                       ".squidsquad/project/worker.md\n"),
        )
        calls = []

        def _recompose(path, **kw):
            calls.append(path)
            if "pm.md" in str(path):
                raise RuntimeError("boom")

        fake_lfw = SimpleNamespace(recompose_path=_recompose)
        fake_cfg = SimpleNamespace(parse_aliases_registry=MagicMock(return_value={}))
        with patch.dict(sys.modules, {
            "l4_file_watcher": fake_lfw,
            "config": fake_cfg,
            "event_bus": SimpleNamespace(emit=MagicMock()),
        }):
            git_ops._recompose_committed_l4_files()  # must not raise
        assert len(calls) == 2
        err = capsys.readouterr().err
        assert "WARNING" in err

    def test_never_raises_on_unexpected_error(self, monkeypatch):
        def _raise(*a, **k):
            raise RuntimeError("unexpected")
        monkeypatch.setattr(git_ops, "_run_list", _raise)
        git_ops._recompose_committed_l4_files()  # must not raise


class TestCliDispatch13672:
    def test_recompose_committed_l4_files_cmd_exits_zero(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["git_ops.py", "recompose-committed-l4-files"])
        with patch.object(git_ops, "_recompose_committed_l4_files") as fn, \
                patch.object(git_ops, "_ensure_hooks_installed"):
            with pytest.raises(SystemExit) as exc:
                git_ops.main()
        assert exc.value.code == 0
        fn.assert_called_once()
