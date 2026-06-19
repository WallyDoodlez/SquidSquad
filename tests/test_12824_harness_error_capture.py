"""Regression for #12824 — harness `POST /events` 500 (assigned-to) could not be
root-caused because the traceback went only to terminal stdout and was lost.

Two additive behaviors land here:

1. **Global exception handler** — any unhandled exception on a harness route is
   persisted (method+path+traceback) to ``.squidsquad/harness-errors.log`` before
   the standard 500 is returned, so the NEXT 500 is diagnosable.
2. **Fail-soft post-append work** in ``receive_event`` — the routing-critical
   ``event_lifecycle.append`` is what wakes event-mode agents; the non-critical
   post-append bookkeeping (``_update_agent_from_event`` / ``_log_event``) is now
   wrapped so a throw there is swallowed (and its traceback persisted) rather than
   500-ing the emission path that carries assigned-to nudges + handoff routing.

Both protect the wake/handoff path #12824 reported as broken.
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
    import harness
    from harness import app, state, event_lifecycle
    _HTTP_OK = True
except Exception:  # pragma: no cover - import guard
    _HTTP_OK = False


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestGlobalExceptionHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.start_time = time.time()
        state.port = 7373
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_handler_is_registered(self):
        """Additive: a handler for the base ``Exception`` is registered so all
        unhandled exceptions route through traceback-capture (not just terminal
        stdout)."""
        self.assertIn(Exception, app.exception_handlers)

    def test_unhandled_exception_returns_500_and_persists_traceback(self):
        """An unhandled throw on the route → standard 500 body + the capture
        helper invoked with a context naming the method, path, and exception."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(event_lifecycle, "append",
                          side_effect=RuntimeError("boom-12824")), \
             patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post(
                "/events",
                json={"event_type": "status-transition", "role": "skill"},
            )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json(), {"detail": "Internal Server Error"})
        mock_persist.assert_called_once()
        ctx = mock_persist.call_args.args[0]
        self.assertIn("POST", ctx)
        self.assertIn("/events", ctx)
        self.assertIn("RuntimeError", ctx)
        self.assertIn("boom-12824", ctx)

    def test_intentional_httpexception_is_not_captured(self):
        """The 400 (missing fields) is an intentional ``HTTPException`` — Starlette
        routes it through its own handler, so it must NOT hit the 500 capture."""
        with patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post("/events", json={"role": "skill"})  # no event_type
        self.assertEqual(resp.status_code, 400)
        mock_persist.assert_not_called()


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestReceiveEventFailSoft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.start_time = time.time()
        state.port = 7373
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_update_agent_throw_is_swallowed_emission_still_200(self):
        """A throw in the non-critical ``_update_agent_from_event`` must NOT 500
        the routing-critical emission — append still ran, response is 200, and
        the traceback is persisted."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(event_lifecycle, "append") as mock_append, \
             patch("harness._update_agent_from_event",
                   side_effect=RuntimeError("update-boom")), \
             patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post(
                "/events",
                json={"event_type": "assigned-to", "role": "skill",
                      "payload": {"target_alias": "skill"}},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})
        mock_append.assert_called_once()  # routing-critical work still happened
        mock_persist.assert_called_once()  # traceback captured

    def test_log_event_throw_is_swallowed_emission_still_200(self):
        """A throw in the non-critical ``_log_event`` is likewise swallowed."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(event_lifecycle, "append") as mock_append, \
             patch("harness._log_event",
                   side_effect=RuntimeError("log-boom")), \
             patch("harness._persist_harness_error") as mock_persist:
            resp = self.client.post(
                "/events",
                json={"event_type": "assigned-to", "role": "skill",
                      "payload": {"target_alias": "skill"}},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})
        mock_append.assert_called_once()
        mock_persist.assert_called_once()


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestPersistHarnessError(unittest.TestCase):
    def test_writes_traceback_to_log_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "sub" / "harness-errors.log"
            with patch("harness._harness_error_log_path", return_value=log_path):
                try:
                    raise ValueError("trace-me-12824")
                except ValueError:
                    harness._persist_harness_error("UNIT /test ctx")
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("UNIT /test ctx", text)
            self.assertIn("ValueError", text)
            self.assertIn("trace-me-12824", text)

    def test_logger_failure_is_swallowed(self):
        """The error-logger runs on the failure path — it must never itself raise
        (else it masks the original fault)."""
        with patch("harness._harness_error_log_path",
                   side_effect=OSError("cannot resolve path")):
            try:
                raise ValueError("x")
            except ValueError:
                # Must not propagate.
                harness._persist_harness_error("ctx")


if __name__ == "__main__":
    unittest.main()
