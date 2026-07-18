"""Regression test for #13611 — the teardown idle-wait loop in
harness._teardown_and_exit read current-state from the harness-root
SQUIDSQUAD_DIR/<role>/ path instead of the agent's own clone (the 3rd site
of the #13345/#13558 bug class). Sibling-clone agents (skill/qa/dm) write
current-state to THEIR OWN clone's .squidsquad/<role>/ — the harness-root
read returned nothing (FileNotFoundError), which was silently swallowed
WITHOUT setting all_idle = False, so a genuinely mid-task sibling-clone
agent read as already-idle on the very first check and got force-killed
immediately instead of its intended up-to-30s grace window.

The fix reuses HarnessState._read_agent_clone_file (added in #13558) and
treats a None result (unresolvable clone, missing/unreadable file) as NOT
confirmed idle.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import harness  # noqa: E402
from harness import AgentState  # noqa: E402


def _write_state(clone, role, content):
    d = Path(clone) / ".squidsquad" / role
    d.mkdir(parents=True, exist_ok=True)
    (d / "current-state").write_text(content, encoding="utf-8")


class TestTeardownIdleWaitReadsOwnClone13611(unittest.TestCase):
    def _run_teardown(self, clone_dir, harness_root_dir=None):
        """Run _teardown_and_exit for a single running role 'skill' whose
        clone is clone_dir. Returns the mock time.sleep call count (0 means
        the idle-wait loop broke on its first check)."""
        agent = AgentState("skill", str(clone_dir))
        agent.intent = AgentState.INTENT_RUNNING

        sleep_mock = MagicMock()
        port_mock = MagicMock()
        port_mock.exists.return_value = False

        patches = [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._needs_boot",
                  return_value=(False, "running", str(clone_dir))),
            patch("harness.boot_remote._get_clone_path", return_value=str(clone_dir)),
            patch.object(harness.state, "get_agent", return_value=agent),
            patch.object(harness.state, "set_agent"),
            patch.object(harness.state, "save_state"),
            patch("harness.time.sleep", sleep_mock),
            patch("harness.HARNESS_PORT_FILE", port_mock),
            patch("harness.reboot_agent._read_claude_pid",
                  return_value=(None, False)),
            patch("harness.os._exit", side_effect=SystemExit),
        ]
        if harness_root_dir is not None:
            patches.append(patch.object(harness, "SQUIDSQUAD_DIR", Path(harness_root_dir)))

        with _apply_all(patches):
            with self.assertRaises(SystemExit):
                harness._teardown_and_exit(0, True)
        return sleep_mock.call_count

    def test_reads_from_clone_not_harness_root_and_breaks_immediately(self):
        """clone has 'idle' current-state; harness-root has nothing at all
        (an isolated temp dir) — the loop must still recognize idle from
        the clone and break on the FIRST check (no time.sleep(5) from the
        idle-wait loop itself -- only the unconditional time.sleep(1)
        immediately before os._exit() at the very end of the function)."""
        with tempfile.TemporaryDirectory() as clone_dir, \
             tempfile.TemporaryDirectory() as harness_root:
            _write_state(clone_dir, "skill", "idle|")
            sleep_calls = self._run_teardown(clone_dir, harness_root)
        self.assertEqual(sleep_calls, 1,
                         "idle in the agent's own clone must break the wait "
                         "loop on the first check (sleep_calls == 1 is just "
                         "the fixed pre-exit sleep, not an idle-wait retry)")

    def test_missing_clone_file_is_not_treated_as_idle(self):
        """clone has NO current-state file — must NOT be silently treated
        as idle (the original bug). The loop must keep waiting (an extra
        time.sleep(5) beyond the fixed pre-exit sleep) rather than breaking
        immediately."""
        with tempfile.TemporaryDirectory() as clone_dir, \
             tempfile.TemporaryDirectory() as harness_root:
            sleep_calls = self._run_teardown(clone_dir, harness_root)
        self.assertGreater(sleep_calls, 1,
                           "a missing current-state file must NOT be "
                           "silently read as idle -- the wait loop must "
                           "keep polling, not force-kill on the first check")

    def test_harness_root_stale_idle_file_ignored(self):
        """A stale 'idle' file sitting at the harness-root path must NOT
        make the loop conclude idle when the agent's OWN clone says
        something else (e.g. genuinely mid-task)."""
        with tempfile.TemporaryDirectory() as clone_dir, \
             tempfile.TemporaryDirectory() as harness_root:
            _write_state(clone_dir, "skill", "verifying|")
            _write_state(harness_root, "skill", "idle|")  # stale/misleading
            sleep_calls = self._run_teardown(clone_dir, harness_root)
        self.assertGreater(sleep_calls, 1,
                           "the harness-root's stale 'idle' file must be "
                           "ignored -- the agent's own clone (genuinely "
                           "mid-task) is authoritative")


def _apply_all(patches):
    from contextlib import ExitStack

    class _Ctx:
        def __enter__(self):
            self._stack = ExitStack()
            for p in patches:
                self._stack.enter_context(p)
            return self

        def __exit__(self, *exc):
            return self._stack.__exit__(*exc)

    return _Ctx()


if __name__ == "__main__":
    unittest.main()
