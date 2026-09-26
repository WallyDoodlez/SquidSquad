"""#14144 -- state branch + worktree retired.

  - Teardown (references/migrations/state_branch_teardown.py): backup first
    (verified bundle + byte-identical worktree copy, gitignored location),
    then worktree + local branch removed; re-run and fresh clone are no-ops.
    Exercised on real local tmp git repos (no remote, no network).
  - Wiring: the harness runs it for every clone at boot, before auto-start,
    production-only.
  - Single location: no runtime code resolves under the retired worktree;
    state-branch config key gone; an old config.md line is ignored.
"""

import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

spec = importlib.util.spec_from_file_location(
    "state_branch_teardown", REPO / "references" / "migrations" / "state_branch_teardown.py")
td = importlib.util.module_from_spec(spec)
spec.loader.exec_module(td)


def git(root, *args):
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                          check=True).stdout


@pytest.fixture
def clone(tmp_path):
    root = tmp_path / "clone"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def with_worktree(clone):
    git(clone, "worktree", "add", "-q", "-b", td.STATE_BRANCH, td.WORKTREE_DIR)
    wt = clone / td.WORKTREE_DIR
    (wt / "skill").mkdir()
    (wt / "skill" / "working-state.md").write_text("# ws\n", encoding="utf-8")
    git(wt, "add", ".")
    git(wt, "commit", "-q", "-m", "cycle 376 state")
    (wt / "diagnostics").mkdir()
    (wt / "diagnostics" / "diagnostic.jsonl").write_text('{"e":1}\n' * 50, encoding="utf-8")
    return clone


class TestTeardown:
    def test_backup_then_teardown(self, with_worktree):
        root = with_worktree
        diag = root / td.WORKTREE_DIR / "diagnostics" / "diagnostic.jsonl"
        size = diag.stat().st_size
        out = td.teardown(root)
        assert out["action"] == "torn-down", out
        backup = Path(out["backup"])
        assert backup.parent == root / ".squidsquad" / "backups"
        # AC1: bundle verifies; diagnostics copy is byte-identical in size
        git(root, "bundle", "verify", out["bundle"])
        assert td.STATE_BRANCH in git(root, "bundle", "list-heads", out["bundle"])
        assert (backup / "worktree" / "diagnostics" / "diagnostic.jsonl").stat().st_size == size
        assert out["files"]["diagnostics/diagnostic.jsonl"] == size
        assert not (backup / "worktree" / ".git").exists()
        # AC2: gone
        assert td.WORKTREE_DIR not in git(root, "worktree", "list")
        assert not (root / td.WORKTREE_DIR).exists()
        assert subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                               f"refs/heads/{td.STATE_BRANCH}"], cwd=str(root)).returncode != 0

    def test_bundle_restores_the_branch(self, with_worktree, tmp_path):
        out = td.teardown(with_worktree)
        restored = tmp_path / "restored"
        subprocess.run(["git", "clone", "-q", out["bundle"], str(restored)], check=True)
        assert "cycle 376 state" in git(restored, "log", "--oneline", "--all")

    def test_rerun_is_noop(self, with_worktree):
        td.teardown(with_worktree)
        assert td.teardown(with_worktree)["action"] == "noop"

    def test_fresh_clone_untouched(self, clone):
        before = sorted(p.name for p in clone.iterdir())
        assert td.teardown(clone) == {"clone": str(clone), "action": "noop"}
        assert sorted(p.name for p in clone.iterdir()) == before
        assert not (clone / ".squidsquad" / "backups").exists()

    def test_branch_without_worktree(self, clone):
        git(clone, "branch", td.STATE_BRANCH)
        out = td.teardown(clone)
        assert out["action"] == "torn-down" and out["bundle"] and out["files"] == {}

    def test_stray_directory_without_worktree(self, clone):
        (clone / td.WORKTREE_DIR / "diagnostics").mkdir(parents=True)
        (clone / td.WORKTREE_DIR / "diagnostics" / "d.jsonl").write_text("x", encoding="utf-8")
        out = td.teardown(clone)
        assert out["action"] == "torn-down" and out["bundle"] is None
        assert (Path(out["backup"]) / "worktree" / "diagnostics" / "d.jsonl").exists()
        assert not (clone / td.WORKTREE_DIR).exists()

    def test_bundle_failure_removes_nothing(self, with_worktree, monkeypatch):
        real = td._git

        def failing(root, *args, **kw):
            if args[:2] == ("bundle", "create"):
                return subprocess.CompletedProcess(args, 1, "", "disk full")
            return real(root, *args, **kw)

        monkeypatch.setattr(td, "_git", failing)
        out = td.teardown(with_worktree)
        assert out["action"] == "error" and "disk full" in out["error"]
        assert (with_worktree / td.WORKTREE_DIR).exists()
        assert td.WORKTREE_DIR in git(with_worktree, "worktree", "list")

    def test_undeletable_directory_keeps_branch_and_registration(self, with_worktree, monkeypatch):
        """Review F1: a locked file must not leave a git-orphaned directory with
        its branch already deleted."""
        monkeypatch.setattr(td.shutil, "rmtree", lambda *a, **k: None)
        real = td._git

        def no_remove(root, *args, **kw):
            if args[:2] == ("worktree", "remove"):
                return subprocess.CompletedProcess(args, 1, "", "file in use")
            return real(root, *args, **kw)

        monkeypatch.setattr(td, "_git", no_remove)
        out = td.teardown(with_worktree)
        assert out["action"] == "error" and "could not be removed" in out["error"]
        assert Path(out["backup"]).exists()
        assert td.WORKTREE_DIR in git(with_worktree, "worktree", "list")
        assert subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                               f"refs/heads/{td.STATE_BRANCH}"], cwd=str(with_worktree)).returncode == 0

    def test_copy_failure_removes_nothing(self, with_worktree, monkeypatch):
        def boom(src, dest):
            raise OSError("path too long")
        monkeypatch.setattr(td, "_copy_tree", boom)
        out = td.teardown(with_worktree)
        assert out["action"] == "error" and "path too long" in out["error"]
        assert (with_worktree / td.WORKTREE_DIR).exists()

    def test_backups_dir_is_gitignored(self):
        assert ".squidsquad/backups/" in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()

    def test_cli(self, clone, capsys):
        assert td.main([str(clone)]) == 0
        assert '"action": "noop"' in capsys.readouterr().out


class TestHarnessWiring:
    def test_runs_in_boot_before_autostart(self):
        import harness
        init = inspect.getsource(harness.lifespan)
        init = init[init.index("def _deferred_init"):]
        assert init.index("_retire_state_branch_in_clones()") < init.index("Auto-starting all agents")

    def test_isolated_harness_skips(self, tmp_path):
        import harness
        with patch.object(harness, "SQUIDSQUAD_DIR", tmp_path / "iso"):
            assert harness._retire_state_branch_in_clones() is None

    def test_production_tears_down_every_clone(self, with_worktree, tmp_path):
        import harness
        other = tmp_path / "other"
        other.mkdir()
        git(other, "init", "-q")
        with patch.object(harness, "REPO_ROOT", with_worktree), \
             patch.object(harness, "SQUIDSQUAD_DIR", with_worktree / ".squidsquad"), \
             patch.object(harness.boot_remote, "_parse_local_config",
                          return_value={"pm": str(with_worktree), "qa": str(other)}):
            (with_worktree / ".squidsquad").mkdir(exist_ok=True)
            harness.REPO_ROOT.joinpath("references", "migrations").mkdir(parents=True)
            (with_worktree / "references" / "migrations" / "state_branch_teardown.py").write_text(
                (REPO / "references" / "migrations" / "state_branch_teardown.py").read_text(
                    encoding="utf-8"), encoding="utf-8")
            results = harness._retire_state_branch_in_clones()
        assert [r["action"] for r in results] == ["torn-down"]  # no-op clone not reported
        assert not (with_worktree / td.WORKTREE_DIR).exists()

    def test_clone_with_live_agent_is_deferred(self, with_worktree):
        """Review F2: never race an agent that may still run pre-#14144 code."""
        import harness
        agent = harness.AgentState("pm")
        agent.claude_pid, agent.clone_path = 4242, str(with_worktree)
        (with_worktree / ".squidsquad").mkdir(exist_ok=True)
        mig = with_worktree / "references" / "migrations"
        mig.mkdir(parents=True)
        (mig / "state_branch_teardown.py").write_text(
            (REPO / "references" / "migrations" / "state_branch_teardown.py").read_text(
                encoding="utf-8"), encoding="utf-8")
        with patch.object(harness, "REPO_ROOT", with_worktree), \
             patch.object(harness, "SQUIDSQUAD_DIR", with_worktree / ".squidsquad"), \
             patch.object(harness.boot_remote, "_parse_local_config", return_value={}), \
             patch.object(harness.boot_remote, "_is_process_alive", lambda pid: pid == 4242), \
             patch.dict(harness.state.agents, {"pm": agent}, clear=True):
            results = harness._retire_state_branch_in_clones()
        assert results[0]["action"] == "deferred" and "pm" in results[0]["error"]
        assert (with_worktree / td.WORKTREE_DIR).exists()


class TestSingleLocation:
    def test_no_runtime_reference_to_retired_worktree(self):
        out = subprocess.run(
            ["git", "grep", "-n", "-e", "squidsquad-state", "-e", "state_bus", "-e", "state_path",
             "--", "references/", ":!references/migrations"],
            cwd=str(REPO), capture_output=True, text=True)
        assert out.stdout == "", out.stdout

    def test_removed_modules_are_gone(self):
        for name in ("state_bus.py", "migrate_state_branch.py"):
            assert not (REPO / "references" / "scripts" / name).exists()
        listed = (REPO / "references" / "installer-files.txt").read_text(encoding="utf-8")
        assert "state_bus.py" not in listed and "migrate_state_branch.py" not in listed
        assert "references/migrations/state_branch_teardown.py" in listed

    def test_state_paths_resolve_under_squidsquad(self):
        import cycle, cycle_pre, cycle_post, diagnostics, model_router
        assert cycle._squid_path("skill/working-state.md") == cycle.SQUIDSQUAD_DIR / "skill/working-state.md"
        assert cycle_pre._squid_path("x") == cycle_pre.SQUID_DIR / "x"
        assert cycle_post._squid_path("x") == cycle_post.SQUID_DIR / "x"
        assert diagnostics.DIAGNOSTICS_DIR == REPO / ".squidsquad" / "diagnostics"
        assert model_router.DIAGNOSTICS_DIR == REPO / ".squidsquad" / "diagnostics"

    def test_state_branch_key_retired_but_old_line_ignored(self, tmp_path):
        import config
        assert "state-branch" not in config.FIELD_MAP
        cfg = tmp_path / "config.md"
        cfg.write_text("## Git Branches\n\n- **Working Branch**: main\n- **State Branch**: squid-squad\n",
                       encoding="utf-8")
        with config.config_path_override(cfg):
            assert config.get_field("working-branch") == "main"
            with pytest.raises(SystemExit):
                config.get_field("state-branch")

    def test_wizard_config_has_no_state_branch(self):
        """Review F3: neither the rendered config nor the persisted install
        spec carries the retired branch."""
        import wizard
        src = inspect.getsource(wizard)
        assert "State Branch" not in src and "squid-squad" not in src
        spec = wizard.generate_default_spec()
        assert "state" not in spec["git_branches"]
