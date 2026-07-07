"""#13369 — boot-drain heavy work must not read as a wedged boot.

Incident: a qa session picked up a full verification run as a cared event in
its BOOT DRAIN (bootup_complete=False for the whole run). At spawn+~630s the
health poller's #12492 zombie-kill consumed progress_liveness()'s
"wedged-boot-timeout" verdict (#13179 bound, BOOT_GRACE_SECONDS=600) and
killed the live, actively-working PID — the merge landed but its bookkeeping
was lost. The bound keyed purely on bootup_complete + spawn age; the activity
signals that were flowing (in_flight_until, last_activity_at) were never
consulted in the booting branch.

The fix (both halves):

- Harness: past the boot grace, the booting branch now consults the same
  explained-silence + activity signals the post-boot path trusts —
  a ceiling-bounded active_pause() reads alive ("booting-<pause>"), and a
  fresh activity heartbeat that POSTDATES this spawn reads alive
  ("booting-active"). A truly-inert boot has neither → still
  "wedged-boot-timeout" at the bound (#13179 preserved); a boot that worked
  then wedged reads wedged once its heartbeat ages past
  ACTIVITY_GRACE_SECONDS — bounded, never wedge-forever.
- Contract: event-mode-contract.md Case A now emits `bootup-complete`
  BEFORE the boot drain (step 4↔5 swap, matching the session-boot diagram
  that always showed booted → drain), so a heavy drain never runs under
  bootup_complete=False in the first place.

These tests pin the harness half (qa's regression direction: booting agent
with recent heartbeats must NOT be killed at the bound; truly-idle booting
agent past the bound MUST still be killed) and the contract half's ordering
at source level.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

from harness import (  # noqa: E402
    ACTIVITY_GRACE_SECONDS,
    BOOT_GRACE_SECONDS,
    TOOL_CALL_MAX_SECONDS,
    AgentState,
)

NOW = 100_000.0
PAST_GRACE = NOW - (BOOT_GRACE_SECONDS + 100)


def _booting_agent_past_grace():
    a = AgentState("qa")  # bootup_complete = False
    a.last_spawn_at = PAST_GRACE
    return a


class TestBootingBoundActivityAware(unittest.TestCase):
    """The #13369 incident shape and its guard rails."""

    def test_in_flight_tool_call_past_grace_is_alive(self):
        """THE incident: past the boot grace, mid-tool-call (in_flight_until
        set by PreToolUse, within TOOL_CALL_MAX) — working, not wedged."""
        a = _booting_agent_past_grace()
        a.in_flight_until = NOW + (TOOL_CALL_MAX_SECONDS - 10)
        alive, reason = a.progress_liveness(NOW)
        self.assertTrue(alive)
        self.assertEqual(reason, "booting-in-flight")

    def test_fresh_post_spawn_activity_past_grace_is_alive(self):
        """Between tool calls (in_flight cleared at PostToolUse) a fresh
        heartbeat that postdates the spawn still reads alive — the poll
        landing in a generation gap must not kill a working boot."""
        a = _booting_agent_past_grace()
        a.last_activity_at = NOW - 30
        alive, reason = a.progress_liveness(NOW)
        self.assertTrue(alive)
        self.assertEqual(reason, "booting-active")

    def test_inert_boot_past_grace_still_wedged(self):
        """#13179 preserved: no pause, no activity — a boot that never
        completes and never works reads wedged at the bound."""
        a = _booting_agent_past_grace()
        alive, reason = a.progress_liveness(NOW)
        self.assertFalse(alive)
        self.assertEqual(reason, "wedged-boot-timeout")

    def test_worked_then_wedged_boot_is_still_caught(self):
        """Bounded, never wedge-forever: activity postdating the spawn but
        aged past ACTIVITY_GRACE_SECONDS no longer excuses the boot."""
        a = _booting_agent_past_grace()
        a.last_activity_at = NOW - (ACTIVITY_GRACE_SECONDS + 5)
        self.assertGreaterEqual(a.last_activity_at, a.last_spawn_at)
        alive, reason = a.progress_liveness(NOW)
        self.assertFalse(alive)
        self.assertEqual(reason, "wedged-boot-timeout")

    def test_pre_spawn_activity_does_not_excuse_wedge(self):
        """Spawn-scoping: a heartbeat carried over from the PRIOR session
        (older than this spawn) must not excuse this boot's wedge."""
        a = _booting_agent_past_grace()
        a.last_activity_at = a.last_spawn_at - 50
        alive, reason = a.progress_liveness(NOW)
        self.assertFalse(alive)
        self.assertEqual(reason, "wedged-boot-timeout")

    def test_stale_in_flight_deadline_does_not_excuse_wedge(self):
        """A never-cleared in_flight_until further out than one legitimate
        tool call is stale (active_pause's own ceiling) — still wedged."""
        a = _booting_agent_past_grace()
        a.in_flight_until = NOW + TOOL_CALL_MAX_SECONDS + 60
        alive, reason = a.progress_liveness(NOW)
        self.assertFalse(alive)
        self.assertEqual(reason, "wedged-boot-timeout")

    def test_within_grace_unchanged(self):
        """Inside the grace the verdict is plain 'booting' — the new signals
        only matter past the bound."""
        a = AgentState("qa")
        a.last_spawn_at = NOW - (BOOT_GRACE_SECONDS - 5)
        alive, reason = a.progress_liveness(NOW)
        self.assertTrue(alive)
        self.assertEqual(reason, "booting")

    def test_booted_agent_path_unchanged(self):
        """bootup_complete=True never enters the booting branch — the
        post-boot verdicts are untouched by #13369."""
        a = AgentState("qa")
        a.bootup_complete = True
        a.last_spawn_at = PAST_GRACE
        alive, reason = a.progress_liveness(NOW)
        self.assertTrue(alive)
        self.assertEqual(reason, "idle-no-dispatch")


class TestContractBootOrderEagerBootupComplete(unittest.TestCase):
    """Contract half — source-level pin on event-mode-contract.md: Case A
    emits bootup-complete BEFORE draining, matching the session-boot diagram
    (references/roles/instructions.md) that has always shown booted → drain."""

    CONTRACT = REPO_ROOT / "references" / "sub-skills" / "common-events" / \
        "event-mode-contract.md"
    DIAGRAM_SRC = REPO_ROOT / "references" / "roles" / "instructions.md"

    def test_announce_precedes_drain_in_case_a(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        announce = text.find("Announce listener-active")
        drain = text.find("Drain events from cursor forward")
        self.assertNotEqual(announce, -1, "Case A must announce listener-active")
        self.assertNotEqual(drain, -1, "Case A must drain from cursor forward")
        self.assertLess(
            announce, drain,
            "bootup-complete must be emitted BEFORE the boot drain — the "
            "drain-then-announce order holds bootup_complete=false through "
            "heavy drain work and the #13179 booting bound kills the "
            "session mid-work (#13369)",
        )

    def test_case_a_names_the_hazard(self):
        """The reorder must carry its rationale — an instruction with no
        stated why gets 'simplified' back into the hazard."""
        text = self.CONTRACT.read_text(encoding="utf-8")
        self.assertIn("#13369", text)
        self.assertIn("before tending any boot-drain event", text)

    def test_diagram_source_still_shows_booted_then_drain(self):
        text = self.DIAGRAM_SRC.read_text(encoding="utf-8")
        booted = text.find("POST booted event")
        drain = text.find("GET events queued before boot")
        self.assertNotEqual(booted, -1)
        self.assertNotEqual(drain, -1)
        self.assertLess(booted, drain)


if __name__ == "__main__":
    unittest.main()
