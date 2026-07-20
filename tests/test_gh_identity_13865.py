"""#13865 -- GH_TOKEN-pinned env for gh API calls.

gh's active account is machine-global mutable state that kept flipping to a
read-only identity during the #13863 incident (live-observed breaking a
pr-create mid-cycle with "GraphQL: must be a collaborator"). #13863 made git
pushes flip-proof; this covers the remaining exposure -- gh API writes
(tracker transitions, labels, comments, PR operations). gh_identity.gh_env()
hands the subprocess wrappers in tracker.py and git_ops.py an env with
GH_TOKEN set to the pinned identity's keyring token (which the gh CLI prefers
over the active account), or None (= inherit, today's behavior) in every
fail-open case.

All subprocess calls mocked -- no real git/gh runs here.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gh_identity
import git_ops
import tracker


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch):
    """Identity/token caches are process-lifetime; isolate tests from each
    other and from any ambient operator token."""
    gh_identity._IDENTITY_CACHE = "unset"
    gh_identity._TOKEN_CACHE = "unset"
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    yield
    gh_identity._IDENTITY_CACHE = "unset"
    gh_identity._TOKEN_CACHE = "unset"


def _arm_subprocess(monkeypatch, get_url=None, token=None):
    """Route gh_identity's own subprocess calls."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[:3] == ["git", "remote", "get-url"]:
            return get_url if get_url is not None else _mock_result(returncode=1)
        if cmd[:3] == ["gh", "auth", "token"]:
            return token if token is not None else _mock_result(returncode=1)
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(gh_identity.subprocess, "run", fake_run)
    return calls


URL_USERINFO = _mock_result(
    stdout="https://WallyDoodlez@github.com/WallyDoodlez/SquidSquad.git\n")
URL_PLAIN = _mock_result(stdout="https://github.com/SomeOwner/SomeRepo.git\n")
TOKEN_OK = _mock_result(stdout="gho_abc123\n")


class TestPinnedIdentity:
    def test_userinfo_wins(self, monkeypatch):
        _arm_subprocess(monkeypatch, get_url=_mock_result(
            stdout="https://PushUser@github.com/OtherOwner/Repo.git\n"))
        assert gh_identity.pinned_identity() == "PushUser"

    def test_owner_fallback(self, monkeypatch):
        _arm_subprocess(monkeypatch, get_url=URL_PLAIN)
        assert gh_identity.pinned_identity() == "SomeOwner"

    def test_ssh_remote_none(self, monkeypatch):
        _arm_subprocess(monkeypatch, get_url=_mock_result(
            stdout="git@github.com:Owner/Repo.git\n"))
        assert gh_identity.pinned_identity() is None

    def test_token_userinfo_rejected_falls_to_owner(self, monkeypatch):
        _arm_subprocess(monkeypatch, get_url=_mock_result(
            stdout="https://user:ghp_secret@github.com/RealOwner/Repo.git\n"))
        assert gh_identity.pinned_identity() == "RealOwner"

    def test_subprocess_error_is_fail_open(self, monkeypatch):
        def boom(cmd, **kw):
            raise OSError("no git")
        monkeypatch.setattr(gh_identity.subprocess, "run", boom)
        assert gh_identity.pinned_identity() is None

    def test_cached(self, monkeypatch):
        calls = _arm_subprocess(monkeypatch, get_url=URL_USERINFO)
        gh_identity.pinned_identity()
        gh_identity.pinned_identity()
        assert len(calls) == 1


class TestPinnedToken:
    def test_token_resolved_and_cached(self, monkeypatch):
        calls = _arm_subprocess(monkeypatch, get_url=URL_USERINFO,
                                token=TOKEN_OK)
        assert gh_identity.pinned_token() == "gho_abc123"
        gh_identity.pinned_token()
        assert len([c for c in calls if c[:2] == ["gh", "auth"]]) == 1

    def test_no_identity_no_token_subprocess(self, monkeypatch):
        calls = _arm_subprocess(monkeypatch, get_url=_mock_result(
            stdout="git@github.com:Owner/Repo.git\n"))
        assert gh_identity.pinned_token() is None
        assert not any(c[:2] == ["gh", "auth"] for c in calls)

    def test_keyring_miss_is_fail_open(self, monkeypatch):
        _arm_subprocess(monkeypatch, get_url=URL_USERINFO,
                        token=_mock_result(returncode=1, stderr="no token"))
        assert gh_identity.pinned_token() is None


class TestGhEnv:
    def _arm_token(self, monkeypatch, token="gho_abc123"):
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: token)

    def test_injects_for_gh_command(self, monkeypatch):
        self._arm_token(monkeypatch)
        env = gh_identity.gh_env(["gh", "issue", "list"])
        assert env is not None
        assert env["GH_TOKEN"] == "gho_abc123"
        # Full ambient env is preserved alongside the injection.
        for k in os.environ:
            assert k in env

    def test_resolved_gh_path_also_matches(self, monkeypatch):
        # tracker.py substitutes cmd[0] with a resolved absolute gh path
        # (_resolve_gh_bin, #9398) BEFORE building the env -- the matcher
        # must recognize gh.exe/gh.cmd basenames, not just the literal "gh".
        self._arm_token(monkeypatch)
        assert gh_identity.gh_env(
            [r"C:\Program Files\GitHub CLI\gh.exe", "issue", "list"]
        ) is not None
        assert gh_identity.gh_env(["/usr/bin/gh", "api", "x"]) is not None

    def test_non_gh_command_inherits(self, monkeypatch):
        self._arm_token(monkeypatch)
        assert gh_identity.gh_env(["git", "push"]) is None
        assert gh_identity.gh_env([]) is None
        # "ghost" must not be mistaken for gh.
        assert gh_identity.gh_env(["ghost", "run"]) is None

    def test_gh_auth_subcommands_exempt(self, monkeypatch):
        """gh auth switch/token/status must see the real keyring state --
        an injected GH_TOKEN would shadow exactly the machinery the pin
        relies on."""
        self._arm_token(monkeypatch)
        assert gh_identity.gh_env(["gh", "auth", "switch", "--user", "X"]) is None
        assert gh_identity.gh_env(["gh", "auth", "token", "--user", "X"]) is None
        assert gh_identity.gh_env(["gh", "auth", "status"]) is None

    def test_operator_env_token_wins(self, monkeypatch):
        self._arm_token(monkeypatch)
        monkeypatch.setenv("GH_TOKEN", "operator-token")
        assert gh_identity.gh_env(["gh", "issue", "list"]) is None
        monkeypatch.delenv("GH_TOKEN")
        monkeypatch.setenv("GITHUB_TOKEN", "operator-token")
        assert gh_identity.gh_env(["gh", "issue", "list"]) is None

    def test_no_token_is_fail_open(self, monkeypatch):
        self._arm_token(monkeypatch, token=None)
        assert gh_identity.gh_env(["gh", "issue", "list"]) is None


class TestTrackerWiring:
    """tracker.py's three gh subprocess wrappers pass gh_identity.gh_env's
    result as env=. None (inherit) must reach subprocess.run unchanged."""

    def _spy_run(self, monkeypatch, module):
        seen = {}

        def fake_run(cmd, **kw):
            seen["cmd"] = cmd
            seen["env"] = kw.get("env", "MISSING")
            return _mock_result(stdout="[]")

        monkeypatch.setattr(module.subprocess, "run", fake_run)
        return seen

    def test_run_list_passes_pinned_env(self, monkeypatch):
        seen = self._spy_run(monkeypatch, tracker)
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: "gho_x")
        tracker._run_list(["gh", "issue", "list"], check=False)
        assert seen["env"] is not None and seen["env"] != "MISSING"
        assert seen["env"]["GH_TOKEN"] == "gho_x"

    def test_run_list_inherits_when_unpinnable(self, monkeypatch):
        seen = self._spy_run(monkeypatch, tracker)
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: None)
        tracker._run_list(["gh", "issue", "list"], check=False)
        assert seen["env"] is None

    def test_run_list_timeout_passes_pinned_env(self, monkeypatch):
        seen = self._spy_run(monkeypatch, tracker)
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: "gho_x")
        tracker._run_list_timeout(["gh", "api", "x"], timeout=5)
        assert seen["env"]["GH_TOKEN"] == "gho_x"

    def test_run_gh_with_body_passes_pinned_env(self, monkeypatch):
        seen = self._spy_run(monkeypatch, tracker)
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: "gho_x")
        tracker._run_gh_with_body(["gh", "issue", "comment", "1"], "hi",
                                  check=False)
        assert seen["env"]["GH_TOKEN"] == "gho_x"

    def test_git_ops_run_list_passes_pinned_env(self, monkeypatch):
        seen = self._spy_run(monkeypatch, git_ops)
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: "gho_x")
        git_ops._run_list(["gh", "pr", "view", "1"], check=False)
        assert seen["env"]["GH_TOKEN"] == "gho_x"

    def test_git_ops_run_list_git_cmd_inherits(self, monkeypatch):
        seen = self._spy_run(monkeypatch, git_ops)
        monkeypatch.setattr(gh_identity, "pinned_token", lambda: "gho_x")
        git_ops._run_list(["git", "status"], check=False)
        assert seen["env"] is None


class TestGitOpsStandaloneContract:
    """git_ops.py must keep working when copied WITHOUT gh_identity.py --
    the post-merge hook copies only git_ops.py into scratch/consumer repos
    (the stdlib-only contract test_bare_merge_fires_hook_end_to_end
    exercises end-to-end). The import is therefore defensive."""

    def test_import_is_wrapped_in_try_except(self):
        src = (SCRIPTS / "git_ops.py").read_text(encoding="utf-8")
        idx = src.index("import gh_identity")
        preceding = src[:idx].rsplit("\n", 3)
        assert any("try:" in line for line in preceding), (
            "git_ops.py's gh_identity import must be defensive (try/except "
            "ImportError) -- a hard import breaks the standalone-copy "
            "post-merge hook path (#13865)"
        )

    def test_fallback_env_fn_inherits(self, monkeypatch):
        # Simulate the standalone copy: force the fallback and confirm gh
        # calls inherit the ambient env rather than crashing.
        seen = {}

        def fake_run(cmd, **kw):
            seen["env"] = kw.get("env", "MISSING")
            return _mock_result(stdout="[]")

        monkeypatch.setattr(git_ops.subprocess, "run", fake_run)
        monkeypatch.setattr(git_ops, "_gh_env", lambda _cmd: None)
        git_ops._run_list(["gh", "pr", "view", "1"], check=False)
        assert seen["env"] is None
