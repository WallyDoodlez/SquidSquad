#!/usr/bin/env python3
"""SquidSquad Thin Launcher — one-shot agent bootstrapper (#4966).

Replaces the wrapper scripts (start-{role}.ps1/.sh). Starts claude in the
agent's clone directory, writes the PID for harness monitoring, and waits
for claude to exit. No respawn loop, no heartbeat, no sentinel file checks.

The harness owns all lifecycle decisions (restart, stop, crash recovery).

Usage:
    python references/scripts/thin_launcher.py <role>

Environment:
    SQUIDSQUAD_ROLE is set automatically by this script before starting claude.

Exit codes:
    0  — claude exited normally
    42 — claude exited with code 42 (context pressure / intent exit)
    1  — error (could not start claude)
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALID_EFFORT_LEVELS = {"low", "medium", "high", "max"}


def _get_effort_level(role):
    """Read per-agent effort level from config.md. Falls back to 'high'."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        level = (get_field(f"effort-{role}") or "high").strip().lower()
        return level if level in VALID_EFFORT_LEVELS else "high"
    except (Exception, SystemExit):
        return "high"


def _write_pid(clone_path, role, pid):
    """Write claude PID for harness monitoring. Atomic write."""
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = pid_file.with_suffix(".tmp")
    tmp.write_text(str(pid), encoding="utf-8")
    tmp.replace(pid_file)


def _clear_pid(clone_path, role):
    """Remove PID file on exit."""
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    try:
        pid_file.unlink(missing_ok=True)
    except OSError:
        pass


def main():
    if len(sys.argv) < 2:
        print("Usage: thin_launcher.py <role>", file=sys.stderr)
        return 1

    role = sys.argv[1]

    # Resolve clone path — CWD should be the clone root (set by harness/boot_remote)
    clone_path = os.getcwd()

    # Set environment
    env = os.environ.copy()
    env["SQUIDSQUAD_ROLE"] = role

    # Read per-agent effort level from config (#5573)
    effort = _get_effort_level(role)
    print(f"[thin-launcher] Starting claude for {role} in {clone_path} (effort={effort})")

    # Use minimal MCP config so account-level plugins (Meta Ads, etc.)
    # don't crowd out built-in deferred tools like Monitor (#7630).
    mcp_config = Path(clone_path) / ".squidsquad" / "mcp-agents.json"

    try:
        # --mcp-config is variadic (<configs...>), so it must be followed by
        # another flag — otherwise it swallows the trailing prompt as a second
        # config path. Place it first; --append-system-prompt terminates it.
        # --strict-mcp-config is required: without it, account-level plugins
        # still load and crowd out built-in deferred tools (#7630).
        cmd = ["claude"]
        if mcp_config.exists():
            cmd.extend(["--mcp-config", str(mcp_config), "--strict-mcp-config"])
        cmd.extend([
            "--append-system-prompt", f"SQUIDSQUAD_ROLE={role}",
            "--name", f"squidsquad-{role}",
            "--effort", effort,
            "--dangerously-skip-permissions",
            "Boot. Begin your first Ralph Loop cycle now.",
        ])

        proc = subprocess.Popen(
            cmd,
            cwd=clone_path,
            env=env,
        )
    except FileNotFoundError:
        print("[thin-launcher] ERROR: 'claude' not found on PATH", file=sys.stderr)
        return 1

    # Write PID for harness monitoring
    _write_pid(clone_path, role, proc.pid)
    print(f"[thin-launcher] claude PID: {proc.pid}")

    # Wait for claude to exit — keeps terminal open
    try:
        exit_code = proc.wait()
    except KeyboardInterrupt:
        # Ctrl+C in terminal — let claude handle it
        try:
            exit_code = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            exit_code = 1

    # Clean up PID file
    _clear_pid(clone_path, role)

    print(f"[thin-launcher] claude exited with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
