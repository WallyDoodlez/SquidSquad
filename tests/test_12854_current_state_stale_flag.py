"""#12854 — current-state CONTENT must not be read as *current* when stale.

A still-alive agent that stops/stalls mid-cycle never reaches cycle_post's
"idle" write, so its `current-state` freezes on the last in-flight phase/desc
(e.g. "implementing|#12142 running full suite"). Past the staleness window that
frozen content is no longer what the agent is doing — but it reads as
authoritative and seeds wrong root-cause theories (the incident: a frozen
"running full suite" sent PM down a hung-suite theory before the operator
supplied the real cause).

The agent cannot self-correct frozen content (it's stopped), so health_check
exposes a reader-side `current_state_stale` flag: True iff the current-state
mtime is older than the staleness threshold. Consumers (PM health checks,
operator, pipeline-sentinel) must treat phase/desc as last-known-stale, not
current, when it is set. The human table marks a stale phase with a leading "~".

(current-state is gitignored, so git never spuriously refreshes its mtime — the
staleness measure is sound. The residual case — distinguishing "stopped mid-suite"
from "genuinely running a suite" *within* the threshold window — needs the
progress-liveness heartbeat from #12271 and is out of scope here.)
"""

import time
from unittest.mock import patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "references" / "scripts"))
import health_check


def _setup_agent(tmp_path, role, state_text=None, state_age_seconds=0, claude_pid=None):
    import os as _os
    squid = tmp_path / ".squidsquad" / role
    squid.mkdir(parents=True, exist_ok=True)
    if state_text is not None:
        state_file = squid / "current-state"
        state_file.write_text(state_text)
        if state_age_seconds > 0:
            mtime = time.time() - state_age_seconds
            _os.utime(state_file, (mtime, mtime))
    if claude_pid is not None:
        (squid / ".claude-pid").write_text(str(claude_pid))
    return tmp_path


class TestCurrentStateStaleFlag:
    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_fresh_content_not_stale(self, _alive, tmp_path):
        clone = _setup_agent(tmp_path, "skill",
                             state_text="implementing|#42 writing tests",
                             state_age_seconds=5, claude_pid=12345)
        r = health_check.check_agent_health("skill", clone, 30)
        assert r["current_state_stale"] is False
        assert r["health"] == "healthy"

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_alive_agent_with_frozen_content_is_flagged_stale(self, _alive, tmp_path):
        """The #12854 incident shape: PID alive, but content frozen past the
        window — the flag must fire so the frozen desc isn't read as current."""
        clone = _setup_agent(tmp_path, "skill",
                             state_text="implementing|#12142 running full suite",
                             state_age_seconds=3700, claude_pid=12345)
        r = health_check.check_agent_health("skill", clone, 30)
        assert r["current_state_stale"] is True
        # content is preserved (not blanked) so diagnosis keeps the last-known
        # info — but it is now explicitly marked stale.
        assert r["current_state_phase"] == "implementing"
        assert r["current_state_desc"] == "#12142 running full suite"

    def test_no_state_file_is_not_stale(self, tmp_path):
        """Absent state is 'unknown', not 'stale' — staleness needs an mtime."""
        clone = _setup_agent(tmp_path, "skill", claude_pid=None)
        r = health_check.check_agent_health("skill", clone, 30)
        assert r["current_state_stale"] is False

    def test_mtime_fallback_stale_sets_flag(self, tmp_path):
        clone = _setup_agent(tmp_path, "skill",
                             state_text="implementing|#7", state_age_seconds=3700)
        r = health_check.check_agent_health("skill", clone, 30)
        assert r["current_state_stale"] is True
        assert r["health"] == "stalled"

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_table_marks_stale_phase_with_tilde(self, _alive, tmp_path):
        clone = _setup_agent(tmp_path, "skill",
                             state_text="implementing|#12142 running full suite",
                             state_age_seconds=3700, claude_pid=12345)
        report = {
            "agents": [health_check.check_agent_health("skill", clone, 30)],
            "interval_minutes": 30, "all_healthy": False,
            "timestamp": "2026-06-21T00:00:00",
        }
        table = health_check.format_table(report)
        assert "~implementing" in table

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_table_does_not_mark_fresh_phase(self, _alive, tmp_path):
        clone = _setup_agent(tmp_path, "skill",
                             state_text="implementing|#42",
                             state_age_seconds=5, claude_pid=12345)
        report = {
            "agents": [health_check.check_agent_health("skill", clone, 30)],
            "interval_minutes": 30, "all_healthy": True,
            "timestamp": "2026-06-21T00:00:00",
        }
        table = health_check.format_table(report)
        assert "~implementing" not in table
        assert "implementing" in table
