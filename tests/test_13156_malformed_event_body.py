"""Regression: harness `POST /events` must fail CLOSED (400) on a malformed
body, not crash with a 500 (#13156).

Before the fix, `receive_event` called `await request.json()` unguarded; a raw
(unescaped) control character in a JSON string field made stdlib `json.loads`
(strict=True) raise `JSONDecodeError`, which propagated to the global exception
handler as a 500 — observed 47x in harness-errors.log, a fixed-position retry
loop. The endpoint must reject malformed input cleanly with 400 instead.
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestMalformedEventBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.start_time = time.time()
        state.port = 7373
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_raw_control_char_body_returns_400_not_500(self):
        """A raw newline (0x0a) inside a JSON string field is invalid per strict
        JSON. The handler must return 400 (fail closed), NOT 500 (crash)."""
        # Literal newline byte inside the "detail" string — the exact shape the
        # bug hit (multi-line text serialized without JSON-escaping).
        raw = b'{"event_type":"booted","role":"skill","payload":{"detail":"line1\nline2"}}'
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post(
                "/events", content=raw,
                headers={"content-type": "application/json"},
            )
        self.assertEqual(resp.status_code, 400, f"expected 400, got {resp.status_code}")
        # The 400 is an intentional HTTPException — it must NOT be captured as a
        # 500 by the global exception handler (#12824).
        mock_persist.assert_not_called()

    def test_raw_control_char_other_position_also_400(self):
        """A different raw control char (0x01) in a string also fails closed."""
        raw = b'{"event_type":"booted","role":"skill","x":"a\x01b"}'
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post(
                "/events", content=raw,
                headers={"content-type": "application/json"},
            )
        self.assertEqual(resp.status_code, 400)
        mock_persist.assert_not_called()

    def test_well_formed_body_still_accepted(self):
        """Control: a properly-escaped body (multi-line via \\n escape) is still
        accepted — the guard rejects only genuinely malformed JSON."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
            resp = self.client.post(
                "/events",
                json={"event_type": "booted", "role": "skill",
                      "payload": {"detail": "line1\nline2"}},  # json= escapes the \n
            )
        # Valid body: stored (200). Not a 400/500.
        self.assertEqual(resp.status_code, 200)
