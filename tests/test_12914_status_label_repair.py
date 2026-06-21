"""#12914 — tracker.py repair-status-labels: clean stale status:pending-ship
orphans off CLOSED issues (the single-status invariant's one-time data repair).

The durable prevention is the unconditional strip-all-prior-status-labels in
``transition()`` (covered by test_12475_force_bypasses_legality.py). This file
covers the repair tool for EXISTING pollution, including the #9837 safety split
(DS-12914 F1/F3): issues WITH status:shipped are unambiguously delivered and
repaired by default; issues WITHOUT it are possible closed-but-undelivered
deliverables and are skipped+warned unless --include-unshipped is passed.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker  # noqa: E402


def _result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def _issue(number, *status_labels):
    return {"number": number,
            "labels": [{"name": s} for s in status_labels] + [{"name": "role:dm"}]}


class TestRepairStatusLabels:
    def _wire(self, monkeypatch, closed_issues):
        """gh path: adapter None, list returns closed_issues, capture edits."""
        edits = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)

        def fake_run_list(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "list"]:
                assert "--state" in cmd and cmd[cmd.index("--state") + 1] == "closed"
                assert "status:pending-ship" in cmd
                return _result(stdout=json.dumps(closed_issues))
            if cmd[:3] == ["gh", "issue", "edit"]:
                edits.append(cmd)
                return _result()
            return _result()

        monkeypatch.setattr(tracker, "_run_list", fake_run_list)
        return edits

    def test_dry_run_plans_safe_set_only_no_edits(self, monkeypatch):
        edits = self._wire(monkeypatch, [
            _issue(101, "status:pending-ship"),                    # no shipped -> skipped
            _issue(102, "status:pending-ship", "status:shipped"),  # safe -> planned
        ])
        planned = tracker.repair_status_labels(apply=False)
        assert [n for n, _ in planned] == [102]
        assert edits == [], "dry-run must not issue any gh edit"

    def test_no_shipped_skipped_by_default(self, monkeypatch):
        """#9837 safety: a closed pending-ship issue WITHOUT shipped may be a
        genuine undelivered deliverable — never stripped without opt-in."""
        edits = self._wire(monkeypatch, [_issue(201, "status:pending-ship")])
        planned = tracker.repair_status_labels(apply=True)
        assert planned == []
        assert edits == [], "ambiguous no-shipped set must be skipped by default"

    def test_apply_keeps_shipped_strips_pending_ship(self, monkeypatch):
        edits = self._wire(monkeypatch,
                            [_issue(202, "status:pending-ship", "status:shipped")])
        planned = tracker.repair_status_labels(apply=True)
        assert planned == [(202, ["status:pending-ship"])]
        assert edits == [["gh", "issue", "edit", "202",
                          "--remove-label", "status:pending-ship"]]
        assert "status:shipped" not in edits[0]

    def test_apply_reduces_multilabel_to_shipped(self, monkeypatch):
        # The #9873 case: approved + pending-ship + shipped on one closed issue.
        edits = self._wire(monkeypatch, [
            _issue(9873, "status:approved", "status:pending-ship", "status:shipped"),
        ])
        planned = tracker.repair_status_labels(apply=True)
        assert planned == [(9873, ["status:approved", "status:pending-ship"])]
        cmd = edits[0]
        assert "status:approved" in cmd and "status:pending-ship" in cmd
        assert "status:shipped" not in cmd

    def test_include_unshipped_strips_only_the_orphan(self, monkeypatch):
        """With explicit opt-in, a no-shipped multi-label issue loses ONLY the
        pending-ship orphan — other status labels are kept (no blanking, F3)."""
        edits = self._wire(monkeypatch, [
            _issue(301, "status:pending-ship"),                      # -> remove pending-ship
            _issue(302, "status:approved", "status:pending-ship"),   # keep approved
        ])
        planned = tracker.repair_status_labels(apply=True, include_unshipped=True)
        assert planned == [(301, ["status:pending-ship"]),
                           (302, ["status:pending-ship"])]
        # 302 keeps status:approved — only the orphan is removed.
        cmd_302 = [c for c in edits if c[3] == "302"][0]
        assert "status:approved" not in cmd_302
        assert cmd_302.count("--remove-label") == 1
        assert "status:pending-ship" in cmd_302

    def test_idempotent_nothing_to_repair(self, monkeypatch):
        edits = self._wire(monkeypatch, [])
        planned = tracker.repair_status_labels(apply=True)
        assert planned == []
        assert edits == []

    def test_gh_list_failure_returns_empty_no_edits(self, monkeypatch):
        edits = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)

        def fake_run_list(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "list"]:
                return _result(stderr="boom", returncode=1)
            edits.append(cmd)
            return _result()

        monkeypatch.setattr(tracker, "_run_list", fake_run_list)
        assert tracker.repair_status_labels(apply=True) == []
        assert edits == []

    def test_page_limit_warning_emitted_when_capped(self, monkeypatch, capsys):
        """DS-12914 F2: a full page (== limit) warns about possible truncation."""
        monkeypatch.setattr(tracker, "_REPAIR_PAGE_LIMIT", 2)
        self._wire(monkeypatch, [
            _issue(401, "status:pending-ship", "status:shipped"),
            _issue(402, "status:pending-ship", "status:shipped"),
        ])
        tracker.repair_status_labels(apply=False)
        err = capsys.readouterr().err
        assert "page limit" in err and "truncated" in err

    def test_adapter_path_safe_set(self, monkeypatch):
        stub = MagicMock()
        stub.list_issues.return_value = [
            _issue(501, "status:pending-ship", "status:shipped")]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: stub)
        planned = tracker.repair_status_labels(apply=True)
        assert planned == [(501, ["status:pending-ship"])]
        assert stub.list_issues.call_args.kwargs.get("state") == "closed"
        stub.edit_labels.assert_called_once_with(
            501, add=[], remove=["status:pending-ship"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
