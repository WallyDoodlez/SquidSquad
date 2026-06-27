"""QA independent verification for #13211 — freshen serialization hoisted into
git_ops.ensure_main_and_pull (covers watcher-burst AND post-merge deploy paths).

Independent angle vs skill's tests: proves the lock is RELEASED after an
exception inside the critical section (no deadlock on the next call) — the
"`with`-inside-`try`" release guarantee — in addition to a direct concurrency
proof. Authored by verifier (qa); preserved permanently.
"""
import os
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import git_ops  # noqa: E402


class TestEnsureMainLockRelease13211(unittest.TestCase):
    def test_lock_releases_after_exception_no_deadlock(self):
        # Exception inside the critical section is caught (Never-raises contract)
        # AND the lock is released, so a subsequent call does not deadlock.
        with patch.object(git_ops, "_run", side_effect=RuntimeError("boom")):
            ok, _ = git_ops.ensure_main_and_pull()
        self.assertFalse(ok)

        result = {}
        def _call():
            result["r"] = git_ops.ensure_main_and_pull()
        with patch.object(git_ops, "_run", side_effect=RuntimeError("boom2")):
            t = threading.Thread(target=_call)
            t.start()
            t.join(timeout=5)
        self.assertFalse(t.is_alive(), "lock leaked — second call deadlocked")

    def test_concurrent_callers_serialized_max_one(self):
        state = {"cur": 0, "max": 0}
        slock = threading.Lock()

        def fake_run(*a, **k):
            with slock:
                state["cur"] += 1
                state["max"] = max(state["max"], state["cur"])
            time.sleep(0.02)
            with slock:
                state["cur"] -= 1
            return SimpleNamespace(returncode=0, stdout="main", stderr="")

        with patch.object(git_ops, "_run", side_effect=fake_run), \
             patch.object(git_ops, "pull", return_value=True):
            threads = [threading.Thread(target=git_ops.ensure_main_and_pull)
                       for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
        self.assertEqual(state["max"], 1,
                         f"_ENSURE_MAIN_LOCK not serializing (max={state['max']})")


if __name__ == "__main__":
    unittest.main()
