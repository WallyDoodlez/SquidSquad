"""Tests for #9772 — ship-counter self-heal in cycle_pre.

When a skill PR squash-merges a feature branch that branched off main BEFORE
a DM ship landed, the branch's stale `.squidsquad/config.md` overwrites the
bumped counter on main. DM has had to manually restore the value twice
(cycles 1120 and 1231). #9772 adds a self-heal in DM's cycle_pre: count
distinct issue numbers in dm/qa ship commits since the last `v*` tag, and if
the on-disk counter is below that, restore.

These tests exercise the helper directly with mocked subprocess + mocked
config so no real git history or filesystem state is touched.
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_pre


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_run(tag_stdout="v0.40.0", log_stdout="", tag_returncode=0, log_returncode=0):
    """Return a fake subprocess.run that responds to `git describe` and `git log`."""

    def _run(cmd, **kwargs):
        if "describe" in cmd:
            return MagicMock(returncode=tag_returncode, stdout=tag_stdout, stderr="")
        if "log" in cmd:
            return MagicMock(returncode=log_returncode, stdout=log_stdout, stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    return _run


# ---------------------------------------------------------------------------
# Regression detection
# ---------------------------------------------------------------------------


class TestReconcileShipCounter:
    """`_reconcile_ship_counter` detects regressions and self-heals."""

    def test_returns_none_when_no_regression(self, monkeypatch):
        """git-derived count (1) <= config count (1) → no action."""
        log = "dm: cycle 100 — ship #500 (counter 0→1)"
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="1"), \
             patch("config.set_field") as mock_set:
            result = cycle_pre._reconcile_ship_counter()
        assert result is None
        mock_set.assert_not_called()

    def test_detects_and_restores_regression(self, monkeypatch):
        """git evidence shows 3 ships; config has 1 → restore to 3."""
        log = "\n".join([
            "dm: cycle 100 — ship #500 (counter 0→1)",
            "qa: cycle 99 — verify+ship #501; counter 1→2",
            "dm: cycle 101 — ship #502 (counter 1→2)",
            "qa: cycle 102 — verify+ship #503; counter 2→3",
        ])
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="1"), \
             patch("config.set_field") as mock_set:
            result = cycle_pre._reconcile_ship_counter()
        # 4 distinct issue numbers (#500..#503) but the tests dedupes per-issue
        # (dm + qa each ship the same issue) — so dm ships #500 #502 and qa
        # ships #501 #503 → 4 distinct issues total.
        assert result is not None
        assert result["detected"] == 1
        assert result["restored"] == 4
        assert result["since_tag"] == "v0.40.0"
        mock_set.assert_called_once_with("shipped-since-bump", "4")

    def test_dedupes_dm_and_qa_ships_of_same_issue(self, monkeypatch):
        """Both dm and qa commit per ship; the issue is counted once."""
        log = "\n".join([
            "qa: cycle 99 — verify+ship #500; counter 0→1",
            "dm: cycle 100 — ship #500 (counter 0→1)",  # same issue
            "qa: cycle 101 — verify+ship #501; counter 1→2",
            "dm: cycle 102 — ship #501 (counter 1→2)",  # same issue
        ])
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="0"), \
             patch("config.set_field") as mock_set:
            result = cycle_pre._reconcile_ship_counter()
        assert result["restored"] == 2  # NOT 4
        mock_set.assert_called_once_with("shipped-since-bump", "2")

    def test_ignores_non_ship_commits(self, monkeypatch):
        """skill/pm commits and 'restore' commits are not counted."""
        log = "\n".join([
            "skill: cycle 1228 — #9415 shipped (PR #9738)",  # skill, not dm/qa
            "pm: triage 8 audit findings",                    # pm, not dm/qa
            "dm: dm: cycle 1231 — restore shipped-since-bump 7→8",  # restore, no '#N'
            "dm: cycle 100 — ship #500",                       # counts
        ])
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="0"), \
             patch("config.set_field") as mock_set:
            result = cycle_pre._reconcile_ship_counter()
        assert result["restored"] == 1
        mock_set.assert_called_once_with("shipped-since-bump", "1")

    def test_returns_none_when_no_tag(self, monkeypatch):
        """No v* tag exists → can't establish window → no action."""
        monkeypatch.setattr(cycle_pre.subprocess, "run",
                            _mock_run(tag_returncode=128, tag_stdout=""))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="5"), \
             patch("config.set_field") as mock_set:
            result = cycle_pre._reconcile_ship_counter()
        assert result is None
        mock_set.assert_not_called()

    def test_returns_none_when_git_log_fails(self, monkeypatch):
        """git log non-zero exit → no action."""
        monkeypatch.setattr(cycle_pre.subprocess, "run",
                            _mock_run(log_returncode=128))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="5"), \
             patch("config.set_field") as mock_set:
            result = cycle_pre._reconcile_ship_counter()
        assert result is None
        mock_set.assert_not_called()

    def test_returns_none_when_config_unreadable(self, monkeypatch):
        """config.get_field raises → no action."""
        log = "dm: cycle 100 — ship #500"
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=ValueError("not int")):
            result = cycle_pre._reconcile_ship_counter()
        assert result is None

    def test_writes_correct_format_to_config(self, monkeypatch):
        """set_field is called with the field name and stringified count."""
        log = "dm: cycle 100 — ship #500\ndm: cycle 101 — ship #501"
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="0"), \
             patch("config.set_field") as mock_set:
            cycle_pre._reconcile_ship_counter()
        mock_set.assert_called_once_with("shipped-since-bump", "2")

    def test_repair_emits_warning_to_stderr(self, monkeypatch, capsys):
        log = "dm: cycle 100 — ship #500"
        monkeypatch.setattr(cycle_pre.subprocess, "run", _mock_run(log_stdout=log))
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="0"), \
             patch("config.set_field"):
            cycle_pre._reconcile_ship_counter()
        err = capsys.readouterr().err
        assert "regression detected" in err
        assert "#9772 self-heal" in err
        assert "v0.40.0" in err


# ---------------------------------------------------------------------------
# Role gating: only DM runs the reconciliation
# ---------------------------------------------------------------------------


class TestRoleGating:
    """The reconcile helper is only called by DM cycle_pre (counter owner)."""

    def test_helper_exists_and_is_callable(self):
        """Sanity: function is exported."""
        assert callable(cycle_pre._reconcile_ship_counter)

    def test_no_other_callsite_in_cycle_pre(self):
        """Grep cycle_pre.py — the function name appears exactly twice:
        once at the def, once at the DM-gated callsite in main()."""
        src = (Path(__file__).resolve().parent.parent /
               "references" / "scripts" / "cycle_pre.py").read_text(encoding="utf-8")
        occurrences = src.count("_reconcile_ship_counter")
        # 1 def + 1 callsite = 2. If anyone adds a non-gated callsite this
        # test catches it (the gating is part of the contract per #9772).
        assert occurrences == 2, (
            f"_reconcile_ship_counter has {occurrences} occurrences in "
            f"cycle_pre.py; expected exactly 2 (def + DM-gated callsite)."
        )

    def test_callsite_is_role_dm_gated(self):
        """The single callsite must be inside an `if role == \"dm\"` guard."""
        src = (Path(__file__).resolve().parent.parent /
               "references" / "scripts" / "cycle_pre.py").read_text(encoding="utf-8")
        # Find the callsite (not the def line)
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if "_reconcile_ship_counter()" in line and "def " not in line:
                # Look back up to 10 lines for the role guard.
                preceding = "\n".join(lines[max(0, i - 10):i])
                assert 'role == "dm"' in preceding, (
                    "callsite is not gated on `role == \"dm\"`; #9772 "
                    "requires DM-only invocation"
                )
                return
        pytest.fail("no callsite of _reconcile_ship_counter() found")
