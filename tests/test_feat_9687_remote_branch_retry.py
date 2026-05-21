"""Regression test for #9687 — _verify_remote_branch retries on initial miss.

Before #9687, _verify_remote_branch hit the remote exactly once. The race
between `git push` returning success locally and the remote refs becoming
visible to `ls-remote` left cycle_post blocking the pending-test
auto-transition. Operator had to apply the transition by hand (observed
on #9665).

After #9687, a single retry-after-sleep handles the propagation window.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_post


def _ls_remote_result(stdout="", returncode=0):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = ""
    return r


class TestVerifyRemoteBranchRetry:
    """#9687: a single retry-after-sleep handles the push→ls-remote race."""

    def test_returns_true_when_branch_present_on_first_attempt(self, monkeypatch):
        """No retry when first ls-remote sees the branch — common case unchanged."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _ls_remote_result(
                stdout="abc123\trefs/heads/squidsquad/task/9687\n",
            )

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="squidsquad/task/{number}"):
            slept = []
            result = cycle_post._verify_remote_branch(
                9687, role="skill", _sleep=slept.append,
            )
        assert result is True
        assert len(calls) == 1  # No retry needed
        assert slept == []      # No sleep needed

    def test_retries_once_when_branch_missing_then_appears(self, monkeypatch):
        """#9687 core fix: first attempt False → sleep → retry True."""
        attempts = []

        def fake_run(cmd, **kw):
            attempts.append(cmd)
            # First attempt: branch absent (push not yet visible)
            # Second attempt: branch present (eventual consistency win)
            if len(attempts) == 1:
                return _ls_remote_result(stdout="")
            return _ls_remote_result(
                stdout="def456\trefs/heads/squidsquad/task/9687\n",
            )

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        slept = []
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="squidsquad/task/{number}"):
            result = cycle_post._verify_remote_branch(
                9687, role="skill", _sleep=slept.append,
            )
        assert result is True   # Retry succeeded
        assert len(attempts) == 2  # Exactly one retry
        assert slept == [2]     # Slept 2 seconds before retry

    def test_returns_false_when_branch_missing_on_both_attempts(self, monkeypatch):
        """Real missing branch (not a race) → return False after retry."""
        attempts = []

        def fake_run(cmd, **kw):
            attempts.append(cmd)
            return _ls_remote_result(stdout="")  # Always empty

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="squidsquad/task/{number}"):
            result = cycle_post._verify_remote_branch(
                9687, role="skill", _sleep=lambda _: None,
            )
        assert result is False
        assert len(attempts) == 2  # Tried twice, both empty

    def test_network_failure_on_first_attempt_returns_none(self, monkeypatch):
        """Non-zero exit on first attempt → return None (no retry, no block)."""
        attempts = []

        def fake_run(cmd, **kw):
            attempts.append(cmd)
            return _ls_remote_result(returncode=128)  # network error

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="squidsquad/task/{number}"):
            result = cycle_post._verify_remote_branch(
                9687, role="skill", _sleep=lambda _: None,
            )
        assert result is None
        # Per the existing contract, network failure → return None
        # immediately, no retry. The retry only fires when the first
        # attempt succeeds-but-empty (the race signature).
        assert len(attempts) == 1

    def test_network_failure_on_retry_returns_none(self, monkeypatch):
        """First attempt empty, retry fails → return None (don't block)."""
        attempts = []

        def fake_run(cmd, **kw):
            attempts.append(cmd)
            if len(attempts) == 1:
                return _ls_remote_result(stdout="")  # empty, triggers retry
            return _ls_remote_result(returncode=128)  # retry network failure

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="squidsquad/task/{number}"):
            result = cycle_post._verify_remote_branch(
                9687, role="skill", _sleep=lambda _: None,
            )
        assert result is None
        assert len(attempts) == 2

    def test_default_sleep_is_time_sleep(self):
        """Without _sleep injection, the function uses time.sleep."""
        # Call signature accepts _sleep=None and falls back to time.sleep.
        # Verified by inspecting that the parameter default is None and
        # the implementation references time.sleep when _sleep is None.
        import inspect
        sig = inspect.signature(cycle_post._verify_remote_branch)
        assert "_sleep" in sig.parameters
        assert sig.parameters["_sleep"].default is None
        source = inspect.getsource(cycle_post._verify_remote_branch)
        assert "time.sleep" in source
