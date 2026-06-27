"""S3 regression guard for #12451 — loop-mode staleness preserved; event-mode
applies no file-age staleness verdict.

`statusline.sh` is the shell renderer and there is no bash-execution test
harness in this repo (see tests/test_statusline_schema.py, which guards the
script via static source assertions). These tests follow that established
convention: they assert the loop-mode mtime→overdue countdown is intact AND
structurally gated to the non-event branch, so:

- AC3: a LOOP-mode agent is still flagged stale on a missed interval
  (the `⏰ +Nm` overdue badge driven by `REMAINING <= 0`).
- AC5 (render-layer cross-check of statusline_data.py's AC5): an EVENT-mode
  agent shows `📡 events` and never reaches the mtime/overdue computation —
  no file-age staleness verdict.

The behavioral statusline_data.py side (cmd_phase / cmd_mode) is covered in
tests/test_12451_statusline_event_model.py.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_STATUSLINE = REPO_ROOT / "references" / "statusline.sh"
LIVE_STATUSLINE = REPO_ROOT / ".squidsquad" / "statusline.sh"


@pytest.fixture(scope="module")
def refs_script():
    return REFERENCES_STATUSLINE.read_text(encoding="utf-8")


class TestLoopModeStalenessPreserved:
    """AC3: loop-mode mtime-based overdue countdown is intact."""

    def test_computes_elapsed_and_remaining_from_mtime(self, refs_script):
        # loop-mode reads current-state mtime and derives an interval countdown
        assert "ELAPSED=$(( (NOW - LAST_MOD) / 60 ))" in refs_script
        assert "REMAINING=$(( INTERVAL - ELAPSED ))" in refs_script

    def test_missed_interval_renders_overdue_badge(self, refs_script):
        # REMAINING <= 0 → the stale/overdue flag operators rely on
        assert 'if [ "$REMAINING" -le 0 ]; then' in refs_script
        assert "⏰ +${OVERDUE}m" in refs_script
        assert "OVERDUE=$(( ELAPSED - INTERVAL ))" in refs_script

    def test_timestamp_source_is_current_state_file(self, refs_script):
        assert 'CYCLE_TIMESTAMP_FILE="$SQDIR/$ROLE/current-state"' in refs_script


class TestEventModeNoStalenessVerdict:
    """AC5 (render layer): event mode shows '📡 events', never the overdue calc."""

    def test_wake_mode_from_statusline_data(self, refs_script):
        assert 'statusline_data.py mode "$ROLE"' in refs_script

    def test_event_mode_shows_events_badge(self, refs_script):
        assert 'if [ "$WAKE_MODE" = "event-driven" ]; then' in refs_script
        assert 'TIMER_STR="📡 events"' in refs_script

    def test_overdue_block_is_gated_to_non_event_branch(self, refs_script):
        """The mtime/overdue computation must live in the `else` (loop) arm of
        the WAKE_MODE branch — so an event-mode agent never gets a file-age
        verdict (#12451 AC5)."""
        # Slice from the WAKE_MODE event-mode test to the end of its else arm.
        start = refs_script.index('if [ "$WAKE_MODE" = "event-driven" ]; then')
        # The overdue computation must appear AFTER the event-mode badge line,
        # i.e. inside the else arm — never before it.
        events_badge = refs_script.index('TIMER_STR="📡 events"', start)
        overdue_calc = refs_script.index("REMAINING=$(( INTERVAL - ELAPSED ))", start)
        assert overdue_calc > events_badge, (
            "overdue computation must be in the loop-mode (else) arm, after the "
            "event-mode '📡 events' badge — otherwise event mode gets a staleness verdict"
        )


class TestStatuslineSync:
    """The two copies must stay byte-identical so the live renderer matches."""

    def test_references_and_live_in_sync_if_present(self, refs_script):
        if not LIVE_STATUSLINE.exists():
            pytest.skip("no live .squidsquad/statusline.sh on this checkout")
        assert LIVE_STATUSLINE.read_text(encoding="utf-8") == refs_script
