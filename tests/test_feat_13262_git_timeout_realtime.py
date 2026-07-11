"""QA independent verification for #13262 — git_ops._run / _run_list must enforce
a real subprocess timeout, translating subprocess.TimeoutExpired into the caller's
existing failure shape (rc=124 for check=False; CalledProcessError for check=True).

Independent angle vs skill's TestRunTimeout (which mocks subprocess.run to raise
TimeoutExpired): drives a REAL subprocess that actually overruns a short timeout,
proving the timeout= is wired to the live subprocess.run and the translation fires
end-to-end. Uses the running Python interpreter as a portable sleeper. Authored by
verifier (qa); preserved permanently.
"""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import git_ops  # noqa: E402

_PY = sys.executable
_SLEEP_SHELL = f'"{_PY}" -c "import time; time.sleep(5)"'
_SLEEP_LIST = [_PY, "-c", "import time; time.sleep(5)"]


@unittest.skipIf(not _PY, "no python interpreter to use as a sleeper")
class TestGitTimeoutRealtime13262(unittest.TestCase):
    def test_run_real_timeout_check_false_returns_124(self):
        res = git_ops._run(_SLEEP_SHELL, check=False, timeout=1)
        self.assertIsInstance(res, subprocess.CompletedProcess)
        self.assertEqual(res.returncode, 124, "a real overrun must yield the rc=124 synthetic failure")

    def test_run_real_timeout_check_true_raises(self):
        with self.assertRaises(subprocess.CalledProcessError) as ei:
            git_ops._run(_SLEEP_SHELL, check=True, timeout=1)
        self.assertEqual(ei.exception.returncode, 124)

    def test_run_list_real_timeout_check_false_returns_124(self):
        res = git_ops._run_list(_SLEEP_LIST, check=False, timeout=1)
        self.assertEqual(res.returncode, 124)

    def test_default_timeout_resolves(self):
        self.assertEqual(git_ops.DEFAULT_GIT_TIMEOUT, 300)
        self.assertEqual(git_ops._git_timeout(), 300)


if __name__ == "__main__":
    unittest.main()
