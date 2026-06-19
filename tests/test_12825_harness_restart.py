"""#12825 — supervised harness launcher + agent-triggerable harness restart.

Covers the deterministic foundation (this slice):

- **AC2** — ``POST /restart`` is distinct from ``/shutdown``: it tears down agents
  and exits with ``HARNESS_RESTART_EXIT_CODE`` (so the supervised launcher
  relaunches), keeping the port file; ``/shutdown`` exits 0 and removes it.
- **AC1** — ``restart-harness.sh`` auto-relaunches on the restart code, stops on a
  clean exit, and gives up after a crash-loop (bash-gated behavioral test).

AC3 (sub-skill), AC4 (catalog), AC5 (installer default), AC6 (compose), AC7 (CQ),
AC8 (DS audit) land in the next slice.
"""

import os
import shutil
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from fastapi.testclient import TestClient
    import harness
    from harness import app, state
    _HTTP_OK = True
except Exception:  # pragma: no cover - import guard
    _HTTP_OK = False


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestRestartEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.start_time = time.time()
        state.port = 7373
        cls.client = TestClient(app, raise_server_exceptions=False)

    def _capture_teardown(self):
        """Patch _teardown_and_exit to record its args (and not exit the process).
        Returns (patcher, recorder dict, done Event)."""
        rec, done = {}, threading.Event()

        def fake(code, delete_port_file):
            rec["args"] = (code, delete_port_file)
            done.set()

        return patch("harness._teardown_and_exit", side_effect=fake), rec, done

    def test_restart_returns_202_and_tears_down_with_restart_code(self):
        p, rec, done = self._capture_teardown()
        with p:
            resp = self.client.post("/restart")
            self.assertTrue(done.wait(3), "teardown thread never ran")
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json()["status"], "restarting")
        # restart → restart exit code, port file PRESERVED (relaunch reuses it)
        self.assertEqual(rec["args"], (harness.HARNESS_RESTART_EXIT_CODE, False))

    def test_shutdown_returns_202_and_tears_down_with_exit_zero(self):
        p, rec, done = self._capture_teardown()
        with p:
            resp = self.client.post("/shutdown")
            self.assertTrue(done.wait(3), "teardown thread never ran")
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json()["status"], "shutting_down")
        # shutdown → exit 0, port file DELETED (harness is gone)
        self.assertEqual(rec["args"], (0, True))

    def test_restart_code_is_distinct_from_clean_exit(self):
        self.assertNotEqual(harness.HARNESS_RESTART_EXIT_CODE, 0)


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestTeardownAndExit(unittest.TestCase):
    def _run(self, exit_code, delete_port_file, port_exists=True):
        """Run _teardown_and_exit with no running agents; return (exit_code,
        port_file_mock)."""
        port_mock = MagicMock()
        port_mock.exists.return_value = port_exists
        with patch("harness.boot_remote._get_all_roles", return_value=[]), \
             patch("harness.time.sleep"), \
             patch("harness.HARNESS_PORT_FILE", port_mock), \
             patch("harness.os._exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                harness._teardown_and_exit(exit_code, delete_port_file)
        return mock_exit, port_mock

    def test_restart_exits_with_restart_code_and_keeps_port_file(self):
        mock_exit, port_mock = self._run(harness.HARNESS_RESTART_EXIT_CODE, False)
        mock_exit.assert_called_once_with(harness.HARNESS_RESTART_EXIT_CODE)
        port_mock.unlink.assert_not_called()

    def test_shutdown_exits_zero_and_deletes_port_file(self):
        mock_exit, port_mock = self._run(0, True, port_exists=True)
        mock_exit.assert_called_once_with(0)
        port_mock.unlink.assert_called_once()


_BASH = shutil.which("bash")


@unittest.skipUnless(_BASH, "bash not available")
class TestSupervisedLauncherSh(unittest.TestCase):
    """AC1 behavioral test: run restart-harness.sh against a stub harness whose
    exit codes are scripted, and verify relaunch / stop / crash-guard."""

    def _run_launcher(self, tmp, stub_body, extra_env=None):
        # Lay out tmp/restart-harness.sh + tmp/references/scripts/harness.py stub.
        scripts = Path(tmp) / "references" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "harness.py").write_text(stub_body, encoding="utf-8")
        shutil.copy2(REPO_ROOT / "restart-harness.sh", Path(tmp) / "restart-harness.sh")
        env = dict(os.environ)
        env["SQUIDSQUAD_HARNESS_CMD"] = f"{sys.executable} references/scripts/harness.py"
        env["SQUIDSQUAD_HARNESS_CRASH_THRESHOLD"] = "3"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [_BASH, "restart-harness.sh"],
            cwd=tmp, env=env, capture_output=True, text=True, timeout=60,
        )

    # Stub: increments a counter file each launch and exits with the code for
    # that launch index from a comma-separated SEQUENCE env var.
    _STUB = (
        "import os\n"
        "c = 'count.txt'\n"
        "n = int(open(c).read()) if os.path.exists(c) else 0\n"
        "open(c, 'w').write(str(n + 1))\n"
        "seq = os.environ['SEQUENCE'].split(',')\n"
        "code = int(seq[n]) if n < len(seq) else 0\n"
        "raise SystemExit(code)\n"
    )

    def test_relaunches_on_restart_code_then_stops_on_clean_exit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            # launch 0 → 42 (relaunch), launch 1 → 42 (relaunch), launch 2 → 0 (stop)
            r = self._run_launcher(tmp, self._STUB, {"SEQUENCE": "42,42,0"})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((Path(tmp) / "count.txt").read_text(), "3")
            self.assertIn("relaunching", r.stdout)
            self.assertIn("exited cleanly", r.stdout)

    def test_crash_loop_guard_gives_up(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            # always exit 1 (crash); guard threshold 3 → give up after 3 launches
            r = self._run_launcher(tmp, self._STUB, {"SEQUENCE": "1,1,1,1,1"})
            self.assertEqual(r.returncode, 1)
            self.assertEqual((Path(tmp) / "count.txt").read_text(), "3")
            self.assertIn("crash-loop detected", r.stderr)


if __name__ == "__main__":
    unittest.main()
