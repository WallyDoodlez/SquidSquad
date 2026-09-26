"""#14108 — unit tests must never reach the live forge.

test_git_ops::test_branch_delete_success ran a REAL `git push origin --delete`
against GitHub (it mocked _run_list but not _git_push). An audit found
siblings: cycle_post tests committing + pushing the live state worktree, a
cycle_pre test running a real `gh issue view`. tests/conftest.py now carries
an autouse guard; these tests pin its decisions.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

import conftest

GIT = shutil.which("git")
needs_git = pytest.mark.skipif(GIT is None, reason="git unavailable")


def git(cwd, *args):
    return conftest._REAL_RUN([GIT, "-C", str(cwd), *args], capture_output=True,
                              text=True, check=False)


def repo_with_origin(tmp_path: Path, url: str) -> Path:
    r = tmp_path / "r"
    conftest._REAL_RUN([GIT, "init", "-q", str(r)], check=True)
    git(r, "remote", "add", "origin", url)
    return r


class TestDecision:
    @pytest.mark.parametrize("url", [
        "https://github.com/o/r.git", "https://user@github.com/o/r.git",
        "ssh://git@github.com/o/r.git", "git@github.com:o/r.git",
    ])
    def test_network_remotes_recognized(self, url):
        assert conftest._is_network_remote(url)

    @pytest.mark.parametrize("url", ["", "/tmp/origin.git",
                                     "C:\\Temp\\origin.git", "../origin.git"])
    def test_local_remotes_not_network(self, url):
        assert not conftest._is_network_remote(url)

    @pytest.mark.parametrize("argv", [
        ["gh", "issue", "view", "1"], ["gh", "pr", "create"],
        ["gh", "api", "user"], ["gh.exe", "label", "list"],
        ["gh", "-R", "o/r", "issue", "list"],
    ])
    def test_gh_forge_verbs_blocked(self, argv):
        assert conftest._live_forge_call(argv, None)

    @pytest.mark.parametrize("argv", [["gh", "--version"], ["gh", "auth", "status"],
                                      ["python", "-V"], []])
    def test_non_forge_commands_allowed(self, argv):
        assert conftest._live_forge_call(argv, None) is None

    @needs_git
    def test_git_push_to_network_origin_blocked(self, tmp_path):
        r = repo_with_origin(tmp_path, "https://example.invalid/o/r.git")
        for verb in ("push", "fetch", "pull", "ls-remote"):
            reason = conftest._live_forge_call(["git", verb, "origin"], str(r))
            assert reason and "network origin" in reason

    @needs_git
    def test_git_push_to_local_origin_allowed(self, tmp_path):
        r = repo_with_origin(tmp_path, str(tmp_path / "origin.git"))
        assert conftest._live_forge_call(["git", "push", "origin", "main"], str(r)) is None

    @needs_git
    def test_git_dash_C_targets_that_repo(self, tmp_path):
        """`git -C <local clone> push` from a cwd whose origin is GitHub is a
        local push (the #13859 two-clone tests); `-C <network repo>` is not."""
        local = repo_with_origin(tmp_path, str(tmp_path / "origin.git"))
        net_parent = tmp_path / "n"
        net_parent.mkdir()
        net = repo_with_origin(net_parent, "https://example.invalid/o/r.git")
        assert conftest._live_forge_call(
            ["git", "-C", str(local), "push", "origin", "main"], str(net)) is None
        assert conftest._live_forge_call(
            ["git", "-C", str(net), "push", "origin", "main"], str(local))

    @needs_git
    def test_non_network_git_verbs_allowed_anywhere(self, tmp_path):
        r = repo_with_origin(tmp_path, "https://example.invalid/o/r.git")
        assert conftest._live_forge_call(["git", "status"], str(r)) is None


class TestFixtureWiring:
    @needs_git
    def test_real_subprocess_run_is_guarded(self, tmp_path):
        r = repo_with_origin(tmp_path, "https://example.invalid/o/r.git")
        with pytest.raises(RuntimeError, match="#14108 live-forge guard"):
            subprocess.run([GIT, "push", "origin", "main"], cwd=str(r),
                           capture_output=True)

    def test_popen_is_guarded(self):
        with pytest.raises(RuntimeError, match="#14108"):
            subprocess.Popen(["gh", "issue", "list"])

    def test_local_git_still_works_through_the_guard(self, tmp_path):
        if GIT is None:
            pytest.skip("git unavailable")
        proc = subprocess.run([GIT, "init", "-q", str(tmp_path / "x")],
                              capture_output=True)
        assert proc.returncode == 0

    @pytest.mark.live_forge
    def test_live_forge_marker_opts_out(self):
        assert subprocess.run is conftest._REAL_RUN
        assert subprocess.Popen is conftest._REAL_POPEN

    def test_integration_dir_is_exempt(self):
        src = Path(conftest.__file__).read_text(encoding="utf-8")
        assert '(REPO_ROOT / "tests" / "integration") in path.parents' in src
