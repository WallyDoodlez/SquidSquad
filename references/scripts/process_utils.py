"""Shared OS-process helpers (#8891).

Cross-platform process liveness used by boot_remote, health_check, and
reboot_agent. thin_launcher.py keeps its own copy of this logic to avoid
importing this module (and indirectly any heavier deps) at boot — see
the comment there. If you change the semantics here, mirror the change
in thin_launcher.py:_is_process_alive.
"""

import os
import platform
import subprocess


def is_process_alive(pid):
    """Return True if a process with this PID is currently running.

    Cross-platform. On Windows we shell out to ``tasklist`` because
    ``os.kill(pid, 0)`` doesn't exist there. On POSIX we use signal 0,
    which only does the permission/existence check without delivering a
    signal.

    Rejects ``None`` and any non-positive PID: ``os.kill(0, 0)`` would
    target the calling process group, and negative PIDs mean process
    groups too — both unsafe to treat as "is this specific process
    alive?". Stay strict so callers can't accidentally probe the wrong
    thing.
    """
    if pid is None or pid <= 0:
        return False
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, check=False,
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False
