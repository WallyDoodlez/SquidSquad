"""Tests for the #9562 harness ProactorEventLoop crash fix.

Background: #9481 fixed the *slow handler* wedge (sync subprocess on the
asyncio loop). But the harness wedged AGAIN at cycle-1521, 30 minutes
after the #9481 ship, with a different signature:

    Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)
    File ".../asyncio/proactor_events.py", line 165, in _call_connection_lost
        self._sock.shutdown(socket.SHUT_RDWR)
    ConnectionResetError: [WinError 10054]

This is a known Python+Windows asyncio bug: when a client resets a
connection (uvicorn keepalive, curl probe, agent poll), the
ProactorEventLoop's cleanup callback raises ConnectionResetError
uncaught, which wedges the HTTP layer. SelectorEventLoop has no such
bug.

The fix: one-line policy switch in ``harness.main()`` *before* uvicorn
starts. Trade-off (no ``asyncio.create_subprocess_exec`` on Windows) is
null — harness uses sync ``subprocess.run`` / ``subprocess.Popen``
everywhere.

This test pins the invariant via source inspection (the policy call
must (a) be inside ``main()``, (b) be gated by ``sys.platform ==
"win32"``, (c) come before uvicorn.Server is instantiated).
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_PATH = REPO_ROOT / "references" / "scripts" / "harness.py"


def _extract_main_body(source: str) -> str:
    """Return the body of ``def main():`` up to the next top-level def."""
    idx = source.find("\ndef main():")
    if idx < 0:
        raise AssertionError(
            "def main(): not found in harness.py — if it was renamed, "
            "update this test too."
        )
    body_start = source.find("\n", idx + 1) + 1
    candidates = [
        source.find("\ndef ", body_start),
        source.find("\nasync def ", body_start),
        source.find("\nclass ", body_start),
        source.find('\nif __name__', body_start),
    ]
    candidates = [c for c in candidates if c > 0]
    end = min(candidates) if candidates else len(source)
    return source[body_start:end]


class TestSelectorEventLoopPolicySetInMain(unittest.TestCase):
    def setUp(self):
        self.source = HARNESS_PATH.read_text(encoding="utf-8")
        self.main_body = _extract_main_body(self.source)

    def test_policy_call_present_in_main(self):
        """``main()`` must call ``set_event_loop_policy(WindowsSelectorEventLoopPolicy())``.

        Without this, the harness HTTP layer wedges on the first
        connection-reset on Windows (#9562, cycle-1521).
        """
        self.assertIn(
            "asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())",
            self.main_body,
            msg=(
                "main() must call "
                "`asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` "
                "before uvicorn starts. The default ProactorEventLoop's "
                "_call_connection_lost cleanup raises ConnectionResetError "
                "uncaught on Windows, wedging the HTTP layer (#9562)."
            ),
        )

    def test_policy_call_is_gated_by_win32(self):
        """The policy switch must be gated by ``sys.platform == "win32"``.

        Selector is the *default* on Linux/macOS; setting Windows policy
        unconditionally would crash on non-Windows platforms (the
        ``WindowsSelectorEventLoopPolicy`` class does not exist there).
        """
        # Find the policy call line index, then walk backward to find
        # the enclosing ``if`` and assert it tests ``sys.platform ==
        # "win32"``.
        lines = self.main_body.splitlines()
        call_idx = None
        for i, line in enumerate(lines):
            if "set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()" in line:
                call_idx = i
                break
        self.assertIsNotNone(
            call_idx, "policy call not found (covered by test above)"
        )

        # Find the nearest preceding ``if`` at a strictly smaller indent.
        call_indent = len(lines[call_idx]) - len(lines[call_idx].lstrip())
        guard_line = None
        for j in range(call_idx - 1, -1, -1):
            stripped = lines[j].lstrip()
            indent = len(lines[j]) - len(stripped)
            if stripped.startswith("if ") and indent < call_indent:
                guard_line = stripped
                break
        self.assertIsNotNone(
            guard_line,
            msg=(
                "policy call must be inside an `if sys.platform == \"win32\":` "
                "guard — WindowsSelectorEventLoopPolicy does not exist on "
                "non-Windows platforms and would AttributeError on import."
            ),
        )
        self.assertTrue(
            re.search(r'sys\.platform\s*==\s*["\']win32["\']', guard_line or ""),
            msg=(
                "expected `if sys.platform == \"win32\":` guard around the "
                f"policy call; found: {guard_line!r}"
            ),
        )

    def test_policy_call_precedes_uvicorn_server(self):
        """The policy must be set BEFORE the uvicorn server is created.

        Once a loop is created (uvicorn.Server.run constructs one), the
        policy change no longer affects that loop. So the order in main()
        matters: policy first, uvicorn second.
        """
        policy_idx = self.main_body.find(
            "set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()"
        )
        uvicorn_idx = self.main_body.find("uvicorn.Server(")
        self.assertGreater(
            policy_idx, -1,
            msg="policy call not found (covered by test above)",
        )
        self.assertGreater(
            uvicorn_idx, -1,
            msg=(
                "uvicorn.Server(...) not found in main() — if the server "
                "construction moved, update this test to assert the new "
                "ordering invariant."
            ),
        )
        self.assertLess(
            policy_idx, uvicorn_idx,
            msg=(
                "policy switch must come before uvicorn.Server(...) — the "
                "policy only affects loops created AFTER it is set."
            ),
        )


if __name__ == "__main__":
    unittest.main()
