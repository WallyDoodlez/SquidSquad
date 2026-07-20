"""#13863 -- flip-proof push credentials + boot-time push-capability gate.

Fleet git pushes broke when (a) the Windows credential-manager entry for the
push identity vanished and (b) gh's machine-global active account flipped to a
read-only identity. `!gh auth git-credential` (#9890) only answers for the
ACTIVE account, so the flip defeated it and every non-interactive push died at
a /dev/tty prompt. The fix pins the push identity derived from the origin URL
via `gh auth token --user X` (flip-independent), persists the healed helper
into each clone's local git config (covers bare `git push` call sites that
bypass _git_push), and gates boot on a dry-run push capability check keyed on
an explicit definitive-failure marker.

All subprocess calls are mocked -- no real git/gh runs here.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


@pytest.fixture(autouse=True)
def _reset_caches():
    """The identity/helper/gh-availability caches are process-lifetime; tests
    must not leak resolutions into each other."""
    git_ops._PUSH_IDENTITY_CACHE = "unset"
    git_ops._PINNED_HELPER_CACHE = "unset"
    git_ops._GH_AVAILABLE_CACHE = None
    yield
    git_ops._PUSH_IDENTITY_CACHE = "unset"
    git_ops._PINNED_HELPER_CACHE = "unset"
    git_ops._GH_AVAILABLE_CACHE = None


def _arm_run_list(monkeypatch, responses):
    """Route git_ops._run_list by command shape. `responses` maps a matcher
    key to a result: 'get-url', 'gh-token', 'config', 'dry-run'."""
    calls = []

    def fake_run_list(cmd, check=True, timeout=None):
        calls.append(cmd)
        joined = " ".join(cmd)
        if "remote get-url" in joined:
            return responses.get("get-url", _mock_result(returncode=1))
        if cmd[:3] == ["gh", "auth", "token"]:
            return responses.get("gh-token", _mock_result(returncode=1))
        if cmd[:3] == ["gh", "auth", "switch"]:
            return responses.get("gh-switch", _mock_result())
        if "config --local" in joined:
            return responses.get("config", _mock_result())
        if "push --dry-run" in joined:
            return responses.get("dry-run", _mock_result())
        raise AssertionError(f"unexpected _run_list call: {cmd}")

    monkeypatch.setattr(git_ops, "_run_list", fake_run_list)
    return calls


HTTPS_USERINFO = _mock_result(stdout="https://WallyDoodlez@github.com/WallyDoodlez/SquidSquad.git\n")
HTTPS_PLAIN = _mock_result(stdout="https://github.com/SomeOwner/SomeRepo.git\n")


# ---------------------------------------------------------------------------
# _resolve_push_identity
# ---------------------------------------------------------------------------

class TestResolvePushIdentity:
    def test_userinfo_wins_over_owner(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": _mock_result(
            stdout="https://PushUser@github.com/OtherOwner/Repo.git\n")})
        assert git_ops._resolve_push_identity() == "PushUser"

    def test_owner_segment_when_no_userinfo(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": HTTPS_PLAIN})
        assert git_ops._resolve_push_identity() == "SomeOwner"

    def test_ssh_remote_returns_none(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": _mock_result(
            stdout="git@github.com:Owner/Repo.git\n")})
        assert git_ops._resolve_push_identity() is None

    def test_token_bearing_userinfo_rejected(self, monkeypatch):
        # https://user:ghp_secret@github.com/... -- never treat the token pair
        # as a username; fall through to the owner segment instead.
        _arm_run_list(monkeypatch, {"get-url": _mock_result(
            stdout="https://user:ghp_secret@github.com/RealOwner/Repo.git\n")})
        assert git_ops._resolve_push_identity() == "RealOwner"

    def test_invalid_username_chars_rejected(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": _mock_result(
            stdout="https://bad$user@github.com/bad$owner/Repo.git\n")})
        assert git_ops._resolve_push_identity() is None

    def test_get_url_failure_returns_none(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": _mock_result(returncode=1)})
        assert git_ops._resolve_push_identity() is None

    def test_cached_after_first_resolution(self, monkeypatch):
        calls = _arm_run_list(monkeypatch, {"get-url": HTTPS_USERINFO})
        git_ops._resolve_push_identity()
        git_ops._resolve_push_identity()
        assert len([c for c in calls if "get-url" in " ".join(c)]) == 1


# ---------------------------------------------------------------------------
# _pinned_credential_helper
# ---------------------------------------------------------------------------

class TestPinnedCredentialHelper:
    def test_pins_user_when_token_available(self, monkeypatch):
        _arm_run_list(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "gh-token": _mock_result(stdout="gho_abc123\n"),
        })
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: True)
        helper = git_ops._pinned_credential_helper()
        assert helper is not None
        assert "username=WallyDoodlez" in helper
        assert "gh auth token --user WallyDoodlez" in helper
        # Only the command goes in config -- never a literal token.
        assert "gho_abc123" not in helper

    def test_none_when_token_missing_from_keyring(self, monkeypatch):
        _arm_run_list(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "gh-token": _mock_result(returncode=1, stderr="no oauth token"),
        })
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: True)
        assert git_ops._pinned_credential_helper() is None

    def test_none_when_no_identity(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": _mock_result(
            stdout="git@github.com:Owner/Repo.git\n")})
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: True)
        assert git_ops._pinned_credential_helper() is None

    def test_none_when_gh_unavailable(self, monkeypatch):
        _arm_run_list(monkeypatch, {"get-url": HTTPS_USERINFO})
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: False)
        assert git_ops._pinned_credential_helper() is None


# ---------------------------------------------------------------------------
# _git_push helper-choice ladder
# ---------------------------------------------------------------------------

class TestGitPushHelperChoice:
    def _push_argv(self, monkeypatch, pinned, gh_available):
        monkeypatch.setattr(git_ops, "_pinned_credential_helper",
                            lambda: pinned)
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: gh_available)
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return _mock_result()

        monkeypatch.setattr(git_ops.subprocess, "run", fake_run)
        git_ops._git_push(["origin", "some-branch"])
        return captured["cmd"]

    def test_pinned_helper_preferred(self, monkeypatch):
        pinned = '!f() { echo username=X; }; f'
        cmd = self._push_argv(monkeypatch, pinned, True)
        assert "credential.helper=" in cmd            # reset entry
        assert "credential.helper=" + pinned in cmd
        assert "credential.helper=!gh auth git-credential" not in cmd

    def test_falls_back_to_generic_gh_helper(self, monkeypatch):
        cmd = self._push_argv(monkeypatch, None, True)
        assert "credential.helper=!gh auth git-credential" in cmd

    def test_no_override_without_gh(self, monkeypatch):
        cmd = self._push_argv(monkeypatch, None, False)
        assert not any("credential.helper" in str(a) for a in cmd)


# ---------------------------------------------------------------------------
# push_doctor
# ---------------------------------------------------------------------------

class TestPushDoctor:
    def _arm(self, monkeypatch, responses, pinned="unset", gh_available=True):
        calls = _arm_run_list(monkeypatch, responses)
        if pinned != "unset":
            monkeypatch.setattr(git_ops, "_pinned_credential_helper",
                                lambda: pinned)
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: gh_available)
        return calls

    def test_non_https_remote_is_noop_pass(self, monkeypatch):
        calls = self._arm(monkeypatch, {"get-url": _mock_result(
            stdout="git@github.com:Owner/Repo.git\n")})
        ok, msg = git_ops.push_doctor()
        assert ok is True
        assert "nothing to heal" in msg
        assert not any("config --local" in " ".join(c) for c in calls)

    def test_persists_reset_plus_pinned_helper(self, monkeypatch):
        pinned = '!f() { echo username=X; }; f'
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(),
        }, pinned=pinned)
        ok, _ = git_ops.push_doctor()
        assert ok is True
        config_calls = [c for c in calls if "config --local" in " ".join(c)]
        assert len(config_calls) == 2
        # First: reset the inherited helper list (empty-string entry).
        assert config_calls[0][-2:] == ["credential.helper", ""]
        assert "--replace-all" in config_calls[0]
        # Second: add the pinned helper.
        assert config_calls[1][-1] == pinned
        assert "--add" in config_calls[1]

    def test_falls_back_to_generic_gh_helper_when_no_pin(self, monkeypatch):
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_PLAIN,
            "dry-run": _mock_result(),
        }, pinned=None, gh_available=True)
        ok, _ = git_ops.push_doctor()
        assert ok is True
        config_calls = [c for c in calls if "config --local" in " ".join(c)]
        assert config_calls[1][-1] == "!gh auth git-credential"

    def test_no_persist_when_gh_absent(self, monkeypatch):
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_PLAIN,
            "dry-run": _mock_result(),
        }, pinned=None, gh_available=False)
        ok, _ = git_ops.push_doctor()
        assert ok is True
        assert not any("config --local" in " ".join(c) for c in calls)

    def test_persist_false_skips_config_writes(self, monkeypatch):
        pinned = '!f() { echo username=X; }; f'
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(),
        }, pinned=pinned)
        git_ops.push_doctor(persist=False)
        assert not any("config --local" in " ".join(c) for c in calls)

    def test_definitive_auth_failure_blocks_with_marker(self, monkeypatch):
        self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(returncode=128, stderr=(
                "fatal: could not read Password for "
                "'https://WallyDoodlez@github.com': No such file or directory")),
        }, pinned=None, gh_available=False)
        ok, msg = git_ops.push_doctor()
        assert ok is False
        assert git_ops.PUSH_DOCTOR_BLOCK_MARKER in msg
        assert "Remediation" in msg

    def test_permission_denied_blocks_with_marker(self, monkeypatch):
        self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(returncode=128, stderr=(
                "remote: Permission to WallyDoodlez/SquidSquad.git denied "
                "to Naahtec.\nfatal: unable to access '...': The requested "
                "URL returned error: 403")),
        }, pinned=None, gh_available=False)
        ok, msg = git_ops.push_doctor()
        assert ok is False
        assert git_ops.PUSH_DOCTOR_BLOCK_MARKER in msg

    def test_non_fast_forward_is_inconclusive_fail_open(self, monkeypatch):
        # A behind-main dry-run rejection is NOT an auth failure -- must pass.
        self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(returncode=1, stderr=(
                "! [rejected]  main -> main (non-fast-forward)")),
        }, pinned=None, gh_available=False)
        ok, msg = git_ops.push_doctor()
        assert ok is True
        assert "inconclusive" in msg
        assert git_ops.PUSH_DOCTOR_BLOCK_MARKER not in msg

    def test_timeout_is_inconclusive_fail_open(self, monkeypatch):
        self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(returncode=124, stderr="timed out"),
        }, pinned=None, gh_available=False)
        ok, msg = git_ops.push_doctor()
        assert ok is True
        assert "inconclusive" in msg


class TestPushDoctorHealActive:
    """#13863 --heal-active: gh auth switch back to the pinned identity --
    the first of the two manual remediation steps, run only when the caller
    (check_gh) has proven the active account read-only."""

    PINNED = '!f() { echo username=X; }; f'

    def _arm(self, monkeypatch, responses, pinned):
        calls = _arm_run_list(monkeypatch, responses)
        monkeypatch.setattr(git_ops, "_pinned_credential_helper",
                            lambda: pinned)
        monkeypatch.setattr(git_ops, "_gh_credential_helper_available",
                            lambda: True)
        return calls

    def test_switches_to_pinned_identity(self, monkeypatch):
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(),
        }, pinned=self.PINNED)
        ok, _ = git_ops.push_doctor(heal_active=True)
        assert ok is True
        switch_calls = [c for c in calls if c[:3] == ["gh", "auth", "switch"]]
        assert switch_calls == [
            ["gh", "auth", "switch", "--user", "WallyDoodlez"]]
        # The switch must precede the dry-run verdict probe.
        assert (calls.index(switch_calls[0])
                < calls.index(next(c for c in calls
                                   if "push --dry-run" in " ".join(c))))

    def test_no_switch_without_pinned_identity(self, monkeypatch):
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_PLAIN,
            "dry-run": _mock_result(),
        }, pinned=None)
        ok, _ = git_ops.push_doctor(heal_active=True)
        assert ok is True
        assert not any(c[:3] == ["gh", "auth", "switch"] for c in calls)

    def test_no_switch_when_heal_not_requested(self, monkeypatch):
        calls = self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "dry-run": _mock_result(),
        }, pinned=self.PINNED)
        git_ops.push_doctor(heal_active=False)
        assert not any(c[:3] == ["gh", "auth", "switch"] for c in calls)

    def test_failed_switch_warns_but_proceeds(self, monkeypatch, capsys):
        self._arm(monkeypatch, {
            "get-url": HTTPS_USERINFO,
            "gh-switch": _mock_result(returncode=1, stderr="boom"),
            "dry-run": _mock_result(),
        }, pinned=self.PINNED)
        ok, _ = git_ops.push_doctor(heal_active=True)
        assert ok is True
        assert "could not switch" in capsys.readouterr().err
