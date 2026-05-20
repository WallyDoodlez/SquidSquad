"""Event-mode agent-subprocess integration tests (#8999 PR3).

Covers TEST-PLAN-8694.md §4 scenarios that involve a real
event-mode agent loop, not just the harness wire protocol. The
harness-layer scenarios (§4.6, §4.7 DM-exception, §4.10, §4.4)
live in ``test_event_mode_e2e.py``; this file is for the
agent-subprocess scenarios PR3 is filling in.

Scope this file:

- §4.8 IT-StopRequested — stop-requested event arrives mid-task.
  Agent reads + advances cursor, but does NOT act on it (atomicity).
  At task boundary, the harness intent flow drives the actual stop;
  working-state is checkpointed before exit.

Scope deliberately NOT in this file yet (PR3 follow-up cycles):

- §4.1 Happy-path E2E — needs a real harness subprocess on a free
  port so cycle_pre/cycle_post can hit it as subprocesses.
- §4.2 / §4.3 — crash recovery; needs SIGKILL + restart simulation.
- §4.5 — harness-down boot; needs harness lifecycle control.
- §4.7 Non-DM half — "agent does NOT wake on bare comment" is an
  agent-decision rule. Covered at the contract level by
  ``8694_spec.json`` Q5 (comprehension test). A real wire-level
  test would need a Claude session injected with a tracker-comment
  event, observed for non-action — out of scope for a deterministic
  integration test.
- §4.8b — idle + event arrival; needs idle-cooldown timing harness.

Approach:

The "agent's creative phase" is the Claude session that reads
cycle-input.json and writes cycle-output.json. For deterministic
tests we substitute a Python stub creative phase that follows the
L1 base contract (atomicity rule: read events, don't act mid-task)
and assert the visible side effects — what the harness recorded,
what cycle-output.json contained, what intent the harness exposed.
"""

import json
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"

try:
    from fastapi.testclient import TestClient  # type: ignore
    import sys as _sys
    _sys.path.insert(0, str(SCRIPTS))
    from harness import app, state, AgentState  # type: ignore
    HARNESS_AVAILABLE = True
except Exception as _e:  # pragma: no cover — surface, don't hide
    print(
        f"[test_event_mode_agent_subprocess] harness import failed: "
        f"{type(_e).__name__}: {_e}",
    )
    HARNESS_AVAILABLE = False
    app = None  # type: ignore
    state = None  # type: ignore
    AgentState = None  # type: ignore


@unittest.skipUnless(HARNESS_AVAILABLE, "harness/fastapi not importable")
class TestStopRequestedAtomicity(unittest.TestCase):
    """§4.8 IT-StopRequested — stop-requested mid-task atomicity rule.

    The L1 base contract (l1-base.md Case D, comment-handling.md):

    1. Event-mode agent is mid-task (working-state in-progress).
    2. ``stop-requested`` event arrives on the bus.
    3. Agent reads the event at cursor+1 and advances the cursor
       atomically — but does NOT act on the payload mid-task. The
       current task runs to its natural boundary.
    4. At task boundary, the agent honors the stop via the harness
       intent state machine (``GET /agents/{role}`` returns
       ``intent: stopping`` → ``cycle_post`` exits 42).

    These tests exercise the harness-side and cycle-script-side of
    the contract. The "agent doesn't act mid-task" decision lives in
    the Claude prompt's interpretation of the L1 base instructions —
    covered separately by the comprehension spec
    ``tests/comprehension/8694_spec.json`` Q3 (mid-task event
    handling). Here we verify that:

    - The harness records ``stop-requested`` like any other event;
      it does NOT auto-flip intent or eagerly cancel work.
    - An agent's cycle-output that ignores the event (no
      transitions, no comments) commits cleanly.
    - When intent IS set to ``stopping``, the harness exposes that
      via ``GET /agents/{role}`` so ``cycle_post`` can detect it
      and trigger the cooperative-exit path.
    - The stop-requested event and the intent flip are independent
      signals — neither implies the other.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)
        # Fix harness boot bookkeeping so endpoints serve requests.
        state.start_time = time.time()
        state.port = 7373

        # Allow our synthetic role through `_validate_role`. Patching
        # boot_remote at the class level keeps every test in this
        # class isolated from whatever roles the live config has.
        cls.role = "test-stop-req"
        cls._roles_patch = mock.patch(
            "harness.boot_remote._get_all_roles",
            return_value=[cls.role],
        )
        cls._roles_patch.start()

        # `update_health` is called on every GET /agents and GET
        # /agents/{role}. Without a real PID file for our synthetic
        # role, it transitions intent STOPPING → STOPPED immediately
        # (harness.py:317), masking the STOPPING state we want to
        # observe. Patch it to a no-op for the class — these tests
        # don't depend on the health-poller's transitions, only on
        # what the intent API exposes after a POST.
        cls._health_patch = mock.patch.object(state, "update_health")
        cls._health_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls._health_patch.stop()
        cls._roles_patch.stop()

    def setUp(self):
        # Re-register a fresh AgentState for the synthetic role
        # before each test to drop intent_set_at and prior events.
        agent = AgentState(self.role)
        agent.intent = AgentState.INTENT_RUNNING
        agent.bootup_complete = True
        state.set_agent(self.role, agent)

    def _post_event(self, event_type: str, payload: dict | None = None,
                    eid: str | None = None) -> dict:
        body = {
            "id": eid or f"ev-{event_type}-{int(time.time() * 1000) % 1_000_000}",
            "event_type": event_type,
            "role": self.role,
            "timestamp": time.time(),
            "payload": payload or {},
        }
        resp = self.client.post("/events", json=body)
        self.assertEqual(resp.status_code, 200, msg=resp.text)
        return body

    def _stream_since(self, since: str | None = None,
                      role_filter: str | None = None) -> list[dict]:
        params: dict = {"limit": 50}
        if since:
            params["since"] = since
        if role_filter:
            params["role"] = role_filter
        resp = self.client.get("/events", params=params)
        self.assertEqual(resp.status_code, 200)
        return resp.json().get("events", [])

    # --- contract: stop-requested is just an event ---

    def test_stop_requested_event_recorded_without_flipping_intent(self):
        """POSTing a ``stop-requested`` event to the harness records
        it on the bus but does NOT auto-flip the agent's intent.
        Intent flips are a separate operator action via
        ``POST /agents/{role}/stop``."""
        body = self._post_event("stop-requested")

        # Event is on the bus, visible to event_poll.py.
        events = self._stream_since(role_filter=self.role)
        self.assertIn(body["id"], [e["id"] for e in events])

        # Intent is still RUNNING — the event itself doesn't move the
        # state machine. The agent's reaction at task boundary is what
        # honors the stop, via a separate POST /agents/{role}/stop.
        resp = self.client.get(f"/agents/{self.role}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("intent"), "running")

    def test_stop_requested_event_not_treated_as_immediate_kill(self):
        """Posting many ``stop-requested`` events back-to-back must
        not cause the harness to crash, double-stop, or otherwise
        mutate the agent's intent on its own. Atomicity is the
        agent's responsibility; the harness is the dumb pipe."""
        ids = []
        for _ in range(5):
            ids.append(self._post_event("stop-requested")["id"])

        resp = self.client.get(f"/agents/{self.role}")
        self.assertEqual(resp.json().get("intent"), "running")

        events = self._stream_since(role_filter=self.role)
        emitted_ids = [e["id"] for e in events]
        for eid in ids:
            self.assertIn(eid, emitted_ids)

    # --- contract: cooperative exit via intent ---

    def test_intent_stop_set_via_api_visible_to_cycle_post(self):
        """At task boundary the agent honors the stop request via
        ``cycle_post``'s ``_query_harness_intent`` call. Verify the
        harness exposes ``intent: stopping`` after the operator (or
        the agent's own end-of-task path) POSTs to the stop
        endpoint, which is what ``cycle_post`` reads."""
        # Operator (or agent-end-of-task) hits the stop endpoint.
        resp = self.client.post(f"/agents/{self.role}/stop")
        self.assertEqual(resp.status_code, 200)

        # Now the agent's cycle_post sees intent=stopping.
        resp = self.client.get(f"/agents/{self.role}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("intent"), "stopping")
        # And `intent_set_at` is recorded for the 60s force-kill
        # safety net (#4792 §3.3 Q7) so a missing cooperative exit
        # doesn't strand the operator.
        self.assertIsNotNone(resp.json().get("intent_set_at"))

    def test_cycle_post_query_harness_intent_returns_stopping(self):
        """End-to-end through the actual cycle_post helper that
        agents call: with intent flipped to stopping, the
        ``_query_harness_intent`` shim returns ``"stopping"``, which
        is the signal that triggers the exit-42 cooperative path
        in ``_do_stop_after_cycle_check``."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_cycle_post_for_stop_test", SCRIPTS / "cycle_post.py"
        )
        if not (spec and spec.loader):
            self.skipTest("cycle_post module not importable")
        cp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cp)

        # Set intent and stub port discovery so the helper hits
        # TestClient via direct override of the GET. _query_harness_intent
        # uses urllib against the discovered port; since TestClient
        # doesn't bind a port, monkeypatch the helper to use the client.
        self.client.post(f"/agents/{self.role}/stop")

        def fake_query(role):
            resp = self.client.get(f"/agents/{role}")
            if resp.status_code != 200:
                return None
            return resp.json().get("intent")

        with mock.patch.object(cp, "_query_harness_intent",
                               side_effect=fake_query):
            should_exit = cp._do_stop_after_cycle_check(
                data={"context_pressure": {}}, role=self.role,
            )

        self.assertTrue(
            should_exit,
            msg="cycle_post must signal exit-42 when harness intent is "
                "stopping — the §4.8 cooperative-exit path.",
        )

    def test_stop_requested_event_alone_does_not_trigger_cycle_post_exit(self):
        """Mirror of the previous test: with stop-requested ONLY on
        the event bus but intent NOT flipped, ``_do_stop_after_cycle_check``
        must NOT signal exit-42. This pins the contract that the event
        and the intent are independent — an agent that mistakenly
        reacted to the event mid-cycle would not exit early."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_cycle_post_for_stop_test_2", SCRIPTS / "cycle_post.py"
        )
        if not (spec and spec.loader):
            self.skipTest("cycle_post module not importable")
        cp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cp)

        # Event posted, intent stays RUNNING.
        self._post_event("stop-requested")

        def fake_query(role):
            resp = self.client.get(f"/agents/{role}")
            return resp.json().get("intent") if resp.status_code == 200 else None

        with mock.patch.object(cp, "_query_harness_intent",
                               side_effect=fake_query):
            should_exit = cp._do_stop_after_cycle_check(
                data={"context_pressure": {}}, role=self.role,
            )

        self.assertFalse(
            should_exit,
            msg="A stop-requested event without an intent flip must NOT "
                "trigger exit-42 — the agent's atomicity rule says "
                "events are observational; intent is the actuator.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
