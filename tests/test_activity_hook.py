"""#12443 — tests for activity_hook.py, the activity-heartbeat poster.

Covers AC2/AC6 fail-open behavior: harness unreachable → no raise, returns
False, exit 0; and the happy path POSTs the heartbeat with the role header.
"""
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import activity_hook  # noqa: E402


class TestPostActivity(unittest.TestCase):
    def test_no_role_returns_false_no_post(self):
        """No role → no-op, never reaches the network."""
        with patch("activity_hook.urllib.request.urlopen") as m:
            self.assertFalse(activity_hook.post_activity("", "PostToolUse"))
            m.assert_not_called()

    def test_unreachable_harness_is_fail_open(self):
        """Connection error → swallowed, returns False, NEVER raises."""
        import urllib.error
        with patch("activity_hook.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("refused")):
            # Must not raise.
            self.assertFalse(
                activity_hook.post_activity("skill", "PostToolUse", port=7373))

    def test_any_exception_is_swallowed(self):
        with patch("activity_hook.urllib.request.urlopen",
                   side_effect=RuntimeError("boom")):
            self.assertFalse(
                activity_hook.post_activity("skill", "PostToolUse", port=7373))

    def test_happy_path_posts_with_role_header(self):
        captured = {}

        class _Resp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["role"] = req.headers.get("X-agent-role")  # urllib title-cases
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp()

        with patch("activity_hook.urllib.request.urlopen", side_effect=_fake_urlopen):
            ok = activity_hook.post_activity(
                "skill", "PostToolUse", tool="Bash", phase="implement", port=7373)
        self.assertTrue(ok)
        self.assertTrue(captured["url"].endswith("/hooks/activity"))
        self.assertEqual(captured["role"], "skill")
        self.assertEqual(captured["body"]["event"], "PostToolUse")
        self.assertEqual(captured["body"]["tool"], "Bash")
        self.assertEqual(captured["body"]["phase"], "implement")

    def test_non_2xx_returns_false(self):
        class _Resp:
            status = 500
            def __enter__(self): return self
            def __exit__(self, *a): return False
        with patch("activity_hook.urllib.request.urlopen", return_value=_Resp()):
            self.assertFalse(
                activity_hook.post_activity("skill", "PostToolUse", port=7373))


class TestMainEntrypoint(unittest.TestCase):
    def test_main_reads_env_role_and_stdin_payload(self):
        payload = {"hook_event_name": "PostToolUseFailure", "tool_name": "Edit"}
        calls = {}

        def _fake_post(role, event, tool=None, **kw):
            calls.update(role=role, event=event, tool=tool)
            return True

        with patch.dict(os.environ, {"SQUIDSQUAD_ROLE": "skill"}), \
             patch("activity_hook.post_activity", side_effect=_fake_post), \
             patch("sys.stdin", io.StringIO(json.dumps(payload))):
            rc = activity_hook.main()
        self.assertEqual(rc, 0)
        self.assertEqual(calls["role"], "skill")
        self.assertEqual(calls["event"], "PostToolUseFailure")
        self.assertEqual(calls["tool"], "Edit")

    def test_main_empty_stdin_still_heartbeats(self):
        """No payload (empty stdin) → still emits a heartbeat (the activity
        FACT is the signal); event defaults, never raises."""
        calls = {}
        with patch.dict(os.environ, {"SQUIDSQUAD_ROLE": "skill"}), \
             patch("activity_hook.post_activity",
                   side_effect=lambda *a, **k: calls.update(a=a) or True), \
             patch("sys.stdin", io.StringIO("")):
            self.assertEqual(activity_hook.main(), 0)
        self.assertEqual(calls["a"][0], "skill")

    def test_main_malformed_stdin_is_fail_open(self):
        with patch.dict(os.environ, {"SQUIDSQUAD_ROLE": "skill"}), \
             patch("activity_hook.post_activity", return_value=True), \
             patch("sys.stdin", io.StringIO("{ not json")):
            self.assertEqual(activity_hook.main(), 0)


if __name__ == "__main__":
    unittest.main()
