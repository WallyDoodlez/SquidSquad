"""Tests for the manual wake-injection primitive `/work/assign` + `tracker.py
work-assign` (#12495).

The primitive emits an `assigned-to` wake to a target alias WITHOUT a status
transition (the distinguishing feature vs `tracker.py transition`) and WITHOUT
rewriting the `role:*` label (a manual re-nudge targets work the agent already
owns, so ownership is unchanged). The harness enforces only alias-existence
(404) + the self-assign invariant (400) — no class-from-class permissions.

Two layers tested:
- harness `POST /work/assign` route (via FastAPI TestClient)
- `tracker.py work_assign()` CLI client (urllib mocked)
"""

import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from fastapi.testclient import TestClient
    import harness  # noqa: F401
    from harness import app, state
    _HTTP_OK = True
except Exception:  # pragma: no cover - import guard
    _HTTP_OK = False

_ALIASES = ["skill", "pm", "qa", "dm"]


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestWorkAssignRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.start_time = time.time()
        state.port = 7373
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_valid_assign_returns_200_and_event_id(self):
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES):
            resp = self.client.post(
                "/work/assign",
                json={"target_alias": "skill", "issue_number": 12495,
                      "event_context": "babysit-test"},
                headers={"X-Squidsquad-Alias": "pm"},
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["event_id"])

    def test_assign_routes_assigned_to_event_to_target(self):
        """The emitted event must be an assigned-to targeting the alias, so the
        target's event_poll surfaces it (wakes target without a transition)."""
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES):
            self.client.post(
                "/work/assign",
                json={"target_alias": "qa", "issue_number": 999,
                      "event_context": "wake-qa"},
                headers={"X-Squidsquad-Alias": "pm"},
            )
            forq = self.client.get("/events/for/qa").json()
        hits = [e for e in forq["events"]
                if e.get("event_type") == "assigned-to"
                and e.get("payload", {}).get("event_context") == "wake-qa"]
        self.assertTrue(hits, "assigned-to with our context not routed to qa")
        self.assertEqual(hits[-1]["payload"]["target_alias"], "qa")
        self.assertEqual(hits[-1]["payload"]["issue_number"], "999")

    def test_unknown_alias_returns_404(self):
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES):
            resp = self.client.post(
                "/work/assign",
                json={"target_alias": "nope"},
                headers={"X-Squidsquad-Alias": "pm"},
            )
        self.assertEqual(resp.status_code, 404)
        detail = resp.json()["detail"]
        self.assertEqual(detail["error"], "unknown alias")
        self.assertEqual(detail["target_alias"], "nope")
        self.assertIn("skill", detail["known_aliases"])

    def test_self_assign_returns_400(self):
        """target_alias == X-Squidsquad-Alias is the structural anti-loop."""
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES):
            resp = self.client.post(
                "/work/assign",
                json={"target_alias": "skill"},
                headers={"X-Squidsquad-Alias": "skill"},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("self-assign", resp.json()["detail"])

    def test_missing_target_alias_returns_400(self):
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES):
            resp = self.client.post(
                "/work/assign", json={"event_context": "x"},
                headers={"X-Squidsquad-Alias": "pm"},
            )
        self.assertEqual(resp.status_code, 400)

    def test_malformed_body_returns_400_not_500(self):
        raw = b'{"target_alias":"skill","x":"a\x01b"}'  # raw control char
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES), \
             patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post(
                "/work/assign", content=raw,
                headers={"content-type": "application/json",
                         "X-Squidsquad-Alias": "pm"},
            )
        self.assertEqual(resp.status_code, 400)
        mock_persist.assert_not_called()

    def test_no_label_rewrite_on_assign(self):
        """The narrow primitive must NOT rewrite the role:* label — no gh
        subprocess call fires during a valid assign (distinguishes it from the
        aspirational universal-router design)."""
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES), \
             patch("harness.subprocess.run") as mock_run:
            resp = self.client.post(
                "/work/assign",
                json={"target_alias": "dm", "issue_number": 5},
                headers={"X-Squidsquad-Alias": "pm"},
            )
        self.assertEqual(resp.status_code, 200)
        mock_run.assert_not_called()

    def test_no_header_skips_self_assign_check(self):
        """Absent X-Squidsquad-Alias → emitter unidentified → invariant skipped,
        assign still succeeds (raw callers aren't blocked)."""
        with patch("harness.boot_remote._get_all_roles", return_value=_ALIASES):
            resp = self.client.post(
                "/work/assign", json={"target_alias": "skill"},
            )
        self.assertEqual(resp.status_code, 200)


class TestTrackerWorkAssignClient(unittest.TestCase):
    def _import_tracker(self):
        import tracker
        return tracker

    def test_posts_to_work_assign_with_header_and_returns_event_id(self):
        tracker = self._import_tracker()
        captured = {}

        class _Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps(
                {"status": "ok", "event_id": "deadbeef"}).encode()

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["data"] = json.loads(req.data.decode())
            captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
            return _Resp()

        with patch("event_bus._discover_port", return_value=7373), \
             patch("urllib.request.urlopen", _fake_urlopen):
            eid = tracker.work_assign("skill", "pm", issue=42,
                                      event_context="process-concern")
        self.assertEqual(eid, "deadbeef")
        self.assertTrue(captured["url"].endswith("/work/assign"))
        self.assertEqual(captured["data"]["target_alias"], "skill")
        self.assertEqual(captured["data"]["issue_number"], "42")
        self.assertEqual(captured["data"]["event_context"], "process-concern")
        # X-Squidsquad-Alias header carries the bare caller alias.
        self.assertEqual(captured["headers"]["x-squidsquad-alias"], "pm")

    def test_decorated_caller_stripped_to_bare_alias(self):
        tracker = self._import_tracker()
        captured = {}

        class _Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps({"event_id": "x"}).encode()

        def _fake_urlopen(req, timeout=None):
            captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
            return _Resp()

        with patch("event_bus._discover_port", return_value=7373), \
             patch("urllib.request.urlopen", _fake_urlopen):
            tracker.work_assign("skill", "pm-lead (pm)")
        self.assertEqual(captured["headers"]["x-squidsquad-alias"], "pm")

    def test_http_error_returns_none(self):
        tracker = self._import_tracker()
        import urllib.error

        def _raise(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {},
                                         MagicMock(read=lambda: b'{"error":"x"}'))

        with patch("event_bus._discover_port", return_value=7373), \
             patch("urllib.request.urlopen", _raise):
            eid = tracker.work_assign("nope", "pm")
        self.assertIsNone(eid)

    def test_bad_payload_json_returns_none(self):
        tracker = self._import_tracker()
        with patch("event_bus._discover_port", return_value=7373):
            eid = tracker.work_assign("skill", "pm", payload="{not json")
        self.assertIsNone(eid)

    def test_port_none_returns_none(self):
        tracker = self._import_tracker()
        with patch("event_bus._discover_port", return_value=None):
            eid = tracker.work_assign("skill", "pm")
        self.assertIsNone(eid)


if __name__ == "__main__":
    unittest.main()
