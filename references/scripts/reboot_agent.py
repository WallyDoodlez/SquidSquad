#!/usr/bin/env python3
"""SquidSquad reboot_agent — helper module for harness-internal process ops.

After #4792 (CONTEXT-4792.md §5.3) this file is reduced to two helpers used
by `harness.py`:

- ``_kill_process(pid)`` — cross-platform FORCE-terminate
  (``taskkill /F`` on Windows, ``SIGKILL`` on POSIX).
- ``_read_claude_pid(clone_path, role)`` — read ``.claude-pid`` and return
  ``(pid, alive)``.

The legacy ``reboot()`` / ``_kill_and_respawn()`` / ``_read_pid_file()``
orchestrators were deleted: agent restart now flows through the harness
intent state machine (POST ``/agents/{role}/restart``). The
``_kill_process`` helper here is the same one the 60s force-kill safety
net in ``harness.update_health`` calls when intent has been STOPPING /
RESTARTING for too long (CONTEXT-4792.md §3.3).

A backward-compatible CLI surface (``main()`` + argparse) is retained
for Phase 2 — operators who invoke ``python references/scripts/reboot_agent.py``
directly still get a clear deprecation pointer. Phase 3 of #8979 removes
the CLI entirely; until then the entry point routes to the harness API.

A separate Phase 6+ task renames this file to ``process_ops.py``.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPT_DIR))
from process_utils import is_process_alive as _is_process_alive  # noqa: E402


def _kill_process(pid):
    """Cross-platform FORCE-kill a process by PID.

    Symmetric semantics on Windows and POSIX:
      - Windows: ``taskkill /F`` — uninterruptible.
      - POSIX:   ``SIGKILL`` — uninterruptible, cannot be caught or masked.

    All callers are force contexts (the 60s safety net in
    ``harness.update_health``, the immediate-kill restart endpoint at
    ``/agents/{role}/restart``, ``/shutdown``, and ``start_team.py --force``).
    Earlier revisions sent ``SIGINT`` on POSIX, but ``SIGINT`` is exactly the
    signal the cooperative shutdown path (``cycle_post`` exit 42 → ``/quit``)
    has already used — so a process that ignored the cooperative shutdown
    is the same one that would ignore ``SIGINT`` here. ``SIGKILL`` is the
    correct semantic match for ``taskkill /F`` and the only signal POSIX
    guarantees cannot be ignored. (CONTEXT-4792.md §3.3 Q7.)

    Best-effort: swallows the case where the process is already dead.
    Callers that need to confirm termination should poll
    ``_is_process_alive(pid)`` after.
    """
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            check=False, capture_output=True,
        )
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # Already dead (PLE) or owned by a different UID (Permission).
            # Both are best-effort no-ops here — the force-kill safety net
            # in update_health will re-check on the next poll, and the
            # operator can fall back to the harness API for diagnostics.
            pass


def _read_claude_pid(clone_path, role):
    """Read the claude subprocess PID from ``.claude-pid``.

    Returns a ``(pid, alive)`` tuple. ``pid`` is ``None`` and ``alive`` is
    ``False`` if the file is missing or unreadable.
    """
    claude_pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    if not claude_pid_file.exists():
        return None, False
    try:
        pid = int(claude_pid_file.read_text(encoding="utf-8").strip())
        return pid, _is_process_alive(pid)
    except (ValueError, OSError):
        return None, False


def main():
    """Deprecated CLI surface — kept for Phase 2 backward compat (#4792).

    Phase 3 of #8979 removes this entry point entirely. Until then, point
    operators at the harness API which now owns restart orchestration.
    """
    print(
        "DEPRECATED: reboot_agent.py CLI is being removed in #4792 Phase 3.\n"
        "Use the harness API instead:\n"
        "  curl -X POST http://127.0.0.1:7373/agents/<role>/restart\n"
        "or via the CLI:\n"
        "  python references/scripts/squidsquad_cli.py restart <role>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
