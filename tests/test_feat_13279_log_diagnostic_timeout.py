"""QA independent verification for #13279 — git_ops._log_diagnostic's subprocess.run
must carry a timeout so a hung diagnostics.py cannot block the calling thread
(the last unguarded git_ops subprocess; completes #13262's hardening).

Independent angle: drives _log_diagnostic with a simulated hung diagnostics
(subprocess.run raising TimeoutExpired) and asserts (a) a timeout= is passed and
(b) the TimeoutExpired is swallowed — the fire-and-forget contract holds, the
caller is never blocked or raised at. Authored by verifier (qa); preserved.
"""
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import git_ops  # noqa: E402


class TestLogDiagnosticTimeout13279(unittest.TestCase):
    def test_timeout_is_passed_to_subprocess(self):
        calls = []

        def cap(*a, **k):
            calls.append(k)
            raise subprocess.TimeoutExpired(cmd="diagnostics.py", timeout=1)

        with patch("subprocess.run", side_effect=cap):
            git_ops._log_diagnostic("warning", "msg")  # must not raise
        self.assertTrue(calls, "_log_diagnostic must call subprocess.run")
        self.assertIn("timeout", calls[0], "subprocess.run must be given a timeout= (#13279)")

    def test_hung_diagnostics_does_not_raise_or_block(self):
        # A hung diagnostics.py surfaces as TimeoutExpired; the fire-and-forget
        # except must swallow it so the caller is never blocked/raised at.
        with patch("subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1)):
            try:
                git_ops._log_diagnostic("warning", "msg")
            except Exception as e:  # noqa: BLE001
                self.fail(f"_log_diagnostic must swallow TimeoutExpired; raised {e!r}")


if __name__ == "__main__":
    unittest.main()
