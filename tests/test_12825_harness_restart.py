"""#12825 — supervised harness launcher + agent-triggerable harness restart.

Covers the deterministic foundation (this slice):

- **AC2** — ``POST /restart`` is distinct from ``/shutdown``: it tears down agents
  and exits with ``HARNESS_RESTART_EXIT_CODE`` (so the supervised launcher
  relaunches), keeping the port file; ``/shutdown`` exits 0 and removes it.
- **AC1** — the consolidated launcher's supervised loop (``.squidsquad/start.sh
  --bare`` / ``start.ps1 --bare``, #13318) auto-relaunches on the restart code,
  stops on a clean exit, and gives up after a crash-loop (behavioral test).

- **AC5** — ``squidsquad_cli._harness_launch_tail`` runs the harness UNDER the
  supervised launcher (``.squidsquad/start.* --bare``) when present (so the
  canonical ``squidsquad_cli start`` path is self-healing), and falls back to bare
  ``harness.py`` when it is absent. The installer manifest ships both launchers.

AC3 (sub-skill), AC4 (catalog), AC6 (compose), AC7 (CQ), AC8 (DS audit) are
verified outside this file (docs / composed output / comprehension specs).
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

    def setUp(self):
        # The teardown guard (#12825 DS-F2) sets a module-global flag that the
        # real process would clear by exiting. Tests reuse the process, so reset
        # it before each case or the second endpoint call would 409.
        harness._teardown_in_progress = False

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

    def test_second_concurrent_teardown_is_rejected_409(self):
        # DS-F2: once a teardown is underway, a second /restart or /shutdown must
        # be rejected (409) rather than spawning a racing second teardown thread.
        p, rec, done = self._capture_teardown()
        with p:
            first = self.client.post("/restart")
            self.assertTrue(done.wait(3), "first teardown thread never ran")
            # Flag is still set (real process would have exited); second loses.
            second = self.client.post("/shutdown")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 409)
        # Only the first teardown ran; its restart args are what was recorded.
        self.assertEqual(rec["args"], (harness.HARNESS_RESTART_EXIT_CODE, False))

    def test_begin_teardown_is_single_winner(self):
        harness._teardown_in_progress = False
        self.assertTrue(harness._begin_teardown())   # first claims the slot
        self.assertFalse(harness._begin_teardown())  # second loses


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
        # Lay out tmp/.squidsquad/start.sh + tmp/references/scripts/harness.py stub.
        # The supervised loop now lives in the consolidated launcher, reached via
        # --bare (skips deps/sync; runs the relaunch loop only). #13318.
        squidsquad_dir = Path(tmp) / ".squidsquad"
        squidsquad_dir.mkdir(parents=True)
        scripts = Path(tmp) / "references" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "harness.py").write_text(stub_body, encoding="utf-8")
        shutil.copy2(REPO_ROOT / ".squidsquad" / "start.sh", squidsquad_dir / "start.sh")
        env = dict(os.environ)
        env["SQUIDSQUAD_HARNESS_CMD"] = f"{sys.executable} references/scripts/harness.py"
        env["SQUIDSQUAD_HARNESS_CRASH_THRESHOLD"] = "3"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [_BASH, str(squidsquad_dir / "start.sh"), "--bare"],
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


@unittest.skipUnless(sys.platform == "win32", "Windows PowerShell launcher path")
class TestSupervisedLauncherPs1(unittest.TestCase):
    """AC1 behavioral test (Windows): run `.squidsquad/start.ps1 --bare` against a
    scripted stub harness and verify relaunch / clean-stop / crash-guard. Mirrors
    the .sh class so both consolidated launchers carry equivalent coverage. #13318
    folded the former restart-harness.bat supervised loop into Invoke-Supervised."""

    _STUB = (
        "import os\n"
        "c = 'count.txt'\n"
        "n = int(open(c).read()) if os.path.exists(c) else 0\n"
        "open(c, 'w').write(str(n + 1))\n"
        "seq = os.environ['SEQUENCE'].split(',')\n"
        "code = int(seq[n]) if n < len(seq) else 0\n"
        "raise SystemExit(code)\n"
    )

    def _run_launcher(self, tmp, extra_env=None):
        squidsquad_dir = Path(tmp) / ".squidsquad"
        squidsquad_dir.mkdir(parents=True)
        scripts = Path(tmp) / "references" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "harness.py").write_text(self._STUB, encoding="utf-8")
        shutil.copy2(REPO_ROOT / ".squidsquad" / "start.ps1", squidsquad_dir / "start.ps1")
        env = dict(os.environ)
        # Forward slashes: Invoke-Supervised space-splits HARNESS_CMD and invokes
        # via `&`, which handles forward-slash paths fine on Windows.
        env["SQUIDSQUAD_HARNESS_CMD"] = f"{sys.executable} references/scripts/harness.py"
        env["SQUIDSQUAD_HARNESS_CRASH_THRESHOLD"] = "3"
        if extra_env:
            env.update(extra_env)
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        return subprocess.run(
            [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(squidsquad_dir / "start.ps1"), "--bare"],
            cwd=tmp, env=env, capture_output=True, text=True, timeout=60,
        )

    def test_relaunches_on_restart_code_then_stops_on_clean_exit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run_launcher(tmp, {"SEQUENCE": "42,42,0"})
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((Path(tmp) / "count.txt").read_text(), "3")
            self.assertIn("relaunching", r.stdout)
            self.assertIn("exited cleanly", r.stdout)

    def test_crash_loop_guard_gives_up(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            # Fast consecutive crashes (elapsed < CRASH_WINDOW) → no reset → trip at 3.
            r = self._run_launcher(tmp, {"SEQUENCE": "1,1,1,1,1"})
            self.assertEqual(r.returncode, 1)
            self.assertEqual((Path(tmp) / "count.txt").read_text(), "3")
            self.assertIn("crash-loop detected", r.stdout + r.stderr)


try:
    import squidsquad_cli
    _CLI_OK = True
except Exception:  # pragma: no cover - import guard
    _CLI_OK = False


@unittest.skipUnless(_CLI_OK, "squidsquad_cli not importable")
class TestCliSupervisedLaunch(unittest.TestCase):
    """AC5 wiring: the canonical `squidsquad_cli start` path spawns the harness
    under the supervised wrapper so POST /restart relaunches in place — with a
    graceful fallback to bare harness.py when the wrapper is absent."""

    def _tail(self, system, ps1_exists, sh_exists):
        ps1 = MagicMock()
        ps1.exists.return_value = ps1_exists
        ps1.__str__ = lambda self: "/repo/.squidsquad/start.ps1"
        sh = MagicMock()
        sh.exists.return_value = sh_exists
        sh.__str__ = lambda self: "/repo/.squidsquad/start.sh"
        with patch.object(squidsquad_cli, "RESTART_WRAPPER_PS1", ps1), \
             patch.object(squidsquad_cli, "RESTART_WRAPPER_SH", sh):
            return squidsquad_cli._harness_launch_tail(system)

    def test_windows_uses_ps1_launcher_bare_when_present(self):
        tail = self._tail("windows", ps1_exists=True, sh_exists=False)
        self.assertEqual(tail, ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-File", "/repo/.squidsquad/start.ps1", "--bare"])

    def test_posix_uses_sh_launcher_bare_via_bash_when_present(self):
        for system in ("darwin", "linux"):
            tail = self._tail(system, ps1_exists=False, sh_exists=True)
            self.assertEqual(tail, ["bash", "/repo/.squidsquad/start.sh", "--bare"])

    def test_falls_back_to_bare_harness_when_wrapper_absent(self):
        for system in ("windows", "darwin", "linux"):
            tail = self._tail(system, ps1_exists=False, sh_exists=False)
            self.assertEqual(tail[0], "python")
            self.assertTrue(tail[1].endswith("harness.py"))

    def test_real_launchers_exist_on_disk(self):
        # The consolidated launchers the manifest ships must be present in .squidsquad/.
        self.assertTrue(squidsquad_cli.RESTART_WRAPPER_PS1.exists())
        self.assertTrue(squidsquad_cli.RESTART_WRAPPER_SH.exists())


if __name__ == "__main__":
    unittest.main()
