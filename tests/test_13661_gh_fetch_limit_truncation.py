"""Regression tests for #13661 — cycle_pre.py's _gh_fetch() call sites for
external-issue triage and pending-ship queries shared the #13555/#13602/#13660
gh --limit 50 silent-truncation class. Live open-issue count is 150+ and gh
orders newest-first, so the external-triage fetch (line ~1058) was silently
missing the oldest ~100 open issues on every triage-external pass.

Fix: raised the three limit=50 call sites to 500 (matching the #13555/#13660
precedent), and centralized a cap-hit WARNING inside _gh_fetch() itself so
every caller — including the pre-existing limit=200 call sites — gets the
self-diagnosing behavior for free.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_pre


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


@pytest.fixture(autouse=True)
def _clear_gh_fetch_cache():
    cycle_pre._GH_FETCH_CACHE.clear()
    yield
    cycle_pre._GH_FETCH_CACHE.clear()


class TestGhFetchCapWarning13661:
    def test_warns_when_result_hits_limit(self, monkeypatch, capsys):
        items = [{"number": i} for i in range(5)]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=__import__("json").dumps(items)),
        )
        cycle_pre._gh_fetch(None, "open", limit=5)
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "#13661" in err

    def test_no_warning_under_limit(self, monkeypatch, capsys):
        items = [{"number": 1}]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=__import__("json").dumps(items)),
        )
        cycle_pre._gh_fetch(None, "open", limit=5)
        err = capsys.readouterr().err
        assert "WARNING" not in err

    def test_no_warning_on_empty_result(self, monkeypatch, capsys):
        monkeypatch.setattr(
            cycle_pre, "_run", lambda cmd, **kw: _mock_result(stdout="[]"),
        )
        cycle_pre._gh_fetch(None, "open", limit=500)
        err = capsys.readouterr().err
        assert "WARNING" not in err

    def test_warning_fires_for_any_limit_value(self, monkeypatch, capsys):
        """The warning is generic to _gh_fetch, not special-cased to the
        raised 500 -- a caller still passing a small limit is still warned."""
        items = [{"number": i} for i in range(200)]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=__import__("json").dumps(items)),
        )
        cycle_pre._gh_fetch("squidsquad", "open", with_comments=True, limit=200)
        err = capsys.readouterr().err
        assert "WARNING" in err


class TestRaisedLimits13661:
    def test_pending_ship_query_uses_raised_limit(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        cycle_pre._gh_fetch(
            "squidsquad,status:pending-ship", "open", with_comments=True, limit=500
        )
        limit_arg = calls[0][calls[0].index("--limit") + 1]
        assert limit_arg == "500"
        assert int(limit_arg) > 50

    def test_external_triage_query_uses_raised_limit(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        cycle_pre._gh_fetch(None, "open", with_body=True, limit=500)
        limit_arg = calls[0][calls[0].index("--limit") + 1]
        assert limit_arg == "500"
        assert int(limit_arg) > 50

    def test_source_no_longer_hardcodes_limit_50(self):
        """#13661: none of _gh_fetch's call sites in cycle_pre.py should still
        pass the old truncating limit=50."""
        source = (SCRIPTS / "cycle_pre.py").read_text(encoding="utf-8")
        assert "limit=50)" not in source
        assert "limit=50\n" not in source
