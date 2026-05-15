#!/usr/bin/env python3
"""SquidSquad remote agent boot — spawn dead agents in new terminals.

Spawns agents via thin launcher (primary) or legacy wrapper scripts (fallback).
Detection uses .health file and .pid for liveness. The harness calls boot_agent()
for auto-reboot; start_team.py calls it for manual boot. Thin launcher writes
.claude-pid for harness PID tracking (#4966).

Usage:
    python scripts/boot_remote.py --role <name>   # Boot a single agent
    python scripts/boot_remote.py --all            # Boot all dead agents
    python scripts/boot_remote.py --dry-run --all  # Show what would be booted
    python scripts/boot_remote.py --json --all     # JSON output
    python scripts/boot_remote.py --help

Exit codes:
    0 — success (spawned, skipped for valid reason, or nothing to do)
    1 — spawn failed or error
    2 — usage error
"""

import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
LOCAL_CONFIG = SQUIDSQUAD_DIR / ".local-config"
CONFIG_MD = SQUIDSQUAD_DIR / "config.md"

# Removed: BOOT_LOG, BOOT_LOCK, COOLDOWN_SECONDS, LOCK_TTL_SECONDS (#2183)


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def _parse_local_config():
    """Parse clone paths → {role: Path(clone_root)}.

    Reads project-local .local-config (scoped to this repo).
    .local-config is mandatory — if missing, exits with a clear error.

    The global ~/.squidsquad/clones/ fallback was removed (#3100) because
    it caused cross-project contamination when stale paths from other
    projects were present (#2750).
    """
    if not LOCAL_CONFIG.exists():
        print(
            f"ERROR: {LOCAL_CONFIG} not found.\n"
            "Run the SquidSquad setup flow to create .local-config, or create it manually.\n"
            "Format: - **role**: /absolute/path/to/clone",
            file=sys.stderr,
        )
        sys.exit(2)

    result = {}

    # .local-config (project-scoped, always correct)
    # Format: `- **role**: <path>` — relative paths resolve against repo root.
    try:
        text = LOCAL_CONFIG.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"-\s*\*\*(\w+)\*\*:\s*(.+)", line)
            if m:
                role = m.group(1).strip()
                raw_path = Path(m.group(2).strip())
                # Resolve relative paths against repo root
                if not raw_path.is_absolute():
                    raw_path = (REPO_ROOT / raw_path).resolve()
                result[role] = raw_path
    except Exception as e:
        print(
            f"ERROR: Failed to parse {LOCAL_CONFIG}: {e}\n"
            "Fix the file or re-run the SquidSquad setup flow.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not result:
        print(
            f"ERROR: {LOCAL_CONFIG} exists but contains no valid entries.\n"
            "Expected format: - **role**: /absolute/path/to/clone",
            file=sys.stderr,
        )
        sys.exit(2)

    return result


def _parse_dev_agents():
    """Read Dev Agents list from config.md → list of role names."""
    if not CONFIG_MD.exists():
        return []
    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        m = re.search(r"Dev Agents\*\*:\s*(.+)", text)
        if m:
            return [a.strip() for a in m.group(1).split(",") if a.strip()]
    except Exception:
        pass
    return []


def _get_all_roles():
    """Get all agent roles from config.md, including PM.

    Only reads the Dev Agents list from config.md — does not scan directories
    or .local-config for extra roles. This prevents booting agents that have
    been removed from config.md but still have leftover directories (#943).
    """
    roles = set(_parse_dev_agents())
    # Fixed team: PM + QA + DM always present (#6261)
    roles.update({"pm", "qa", "dm"})
    return sorted(roles)


def _get_clone_path(role):
    """Get the clone root path for a role. Falls back to REPO_ROOT.

    Returns str (not Path) so the value is JSON-serializable when stored
    in AgentState and written to .harness-state.json.
    """
    local = _parse_local_config()
    return str(local.get(role, REPO_ROOT))


# ---------------------------------------------------------------------------
# PID-based process detection
# ---------------------------------------------------------------------------

def _read_pid_file(clone_path, role):
    """Read PID from .squidsquad/{role}/.pid. Returns int or None.

    Handles UTF-16 LE encoding (PowerShell's $PID > $PidFile writes BOM).
    """
    pid_file = Path(clone_path) / ".squidsquad" / role / ".pid"
    if not pid_file.exists():
        return None
    try:
        raw = pid_file.read_bytes()
        # Detect UTF-16 LE BOM (PowerShell output)
        if raw.startswith(b"\xff\xfe"):
            content = raw.decode("utf-16-le").strip()
        else:
            content = raw.decode("utf-8", errors="replace").strip()
        # Strip BOM character if present after decode
        content = content.lstrip("\ufeff").strip()
        return int(content) if content else None
    except (ValueError, OSError):
        return None


def _is_process_alive(pid):
    """Check if a process with the given PID is still running."""
    if pid is None:
        return False
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, check=False,
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _has_stop_sentinel(clone_path, role):
    """Check if .squidsquad/{role}/.stop exists."""
    stop_file = Path(clone_path) / ".squidsquad" / role / ".stop"
    return stop_file.exists()


# Max age of .booting sentinel before it's considered stale (seconds)
BOOTING_SENTINEL_TTL = 30


def _has_booting_sentinel(clone_path, role):
    """Check if a recent .booting sentinel exists (boot in progress).

    Returns True if .booting exists and is younger than BOOTING_SENTINEL_TTL.
    Stale sentinels (from crashed boot attempts) are ignored.
    """
    booting_file = Path(clone_path) / ".squidsquad" / role / ".booting"
    if not booting_file.exists():
        return False
    try:
        age = time.time() - booting_file.stat().st_mtime
        if age <= BOOTING_SENTINEL_TTL:
            return True
        # Stale sentinel — clean it up
        booting_file.unlink(missing_ok=True)
        return False
    except OSError:
        return False


def _write_booting_sentinel(clone_path, role):
    """Write .booting sentinel to claim the boot slot for a role.

    Uses atomic write (write to .tmp then rename) to avoid races.
    Returns True if sentinel was written (we got the slot), False if
    another boot is already in progress.
    """
    squid_dir = Path(clone_path) / ".squidsquad" / role
    booting_file = squid_dir / ".booting"

    # Check if another boot is in progress
    if _has_booting_sentinel(clone_path, role):
        return False

    # Write atomically
    try:
        squid_dir.mkdir(parents=True, exist_ok=True)
        tmp = squid_dir / ".booting.tmp"
        tmp.write_text(str(os.getpid()), encoding="utf-8")
        tmp.replace(booting_file)
        return True
    except OSError:
        return False


def _clear_booting_sentinel(clone_path, role):
    """Remove .booting sentinel after boot completes or fails."""
    booting_file = Path(clone_path) / ".squidsquad" / role / ".booting"
    try:
        booting_file.unlink(missing_ok=True)
    except OSError:
        pass


def _clean_stale_restart(clone_path, role):
    """Remove .restart sentinel when booting a dead agent (#3349).

    If the agent is dead and has a .restart sentinel, it's stale — from a
    previous reboot_agent request that was never processed. Removing it
    prevents the wrapper from triggering an unwanted extra respawn on fresh boot.
    """
    restart_file = Path(clone_path) / ".squidsquad" / role / ".restart"
    if restart_file.exists():
        try:
            restart_file.unlink()
        except OSError:
            pass




def _read_health_file(clone_path, role):
    """Read .health file for a role. Returns (status, detail) or (None, None).

    Supports two formats (aligned with health_check.py):
    - New (heartbeat epoch): file contains a Unix epoch integer (e.g. "1745366400").
      Wrapper writes this every 5s. Returns ("heartbeat", epoch_str).
    - Legacy (status string): "status" or "status|detail".
      Valid statuses: booting, alive, restarting, backoff, dead, error.
    """
    health_file = Path(clone_path) / ".squidsquad" / role / ".health"
    if not health_file.exists():
        return None, None
    try:
        content = health_file.read_text(encoding="utf-8").strip()
        if not content:
            return None, None
        line = content.split("\n")[0].strip()
        # New format: pure epoch integer (10+ digits)
        if line.isdigit() and len(line) >= 10:
            return "heartbeat", line
        # Legacy format: status|detail
        parts = line.split("|", 1)
        status = parts[0].strip()
        detail = parts[1].strip() if len(parts) > 1 else ""
        return status, detail
    except (OSError, UnicodeDecodeError):
        return None, None


def _needs_boot(role):
    """Determine if an agent needs booting.

    Checks (in order): .stop sentinel, .booting lock, .claude-pid, .pid.
    Returns (needs_boot, reason, clone_path).
    """
    clone_path = _get_clone_path(role)

    # .stop sentinel — agent was explicitly stopped (harness fallback)
    stop_file = Path(clone_path) / ".squidsquad" / role / ".stop"
    if stop_file.exists():
        return False, ".stop sentinel present", str(clone_path)

    # .booting sentinel — another boot is already in progress
    if _has_booting_sentinel(clone_path, role):
        return False, "boot already in progress", str(clone_path)

    # Primary: .claude-pid (written by thin_launcher)
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if _is_process_alive(pid):
                return False, f"alive (PID {pid})", str(clone_path)
            else:
                return True, f"dead (PID {pid})", str(clone_path)
        except (ValueError, OSError) as e:
            print(f"WARNING: corrupt .claude-pid for {role}: {e}", file=sys.stderr)

    # Fallback: legacy .pid file
    pid = _read_pid_file(clone_path, role)
    if pid:
        if _is_process_alive(pid):
            return False, f"alive (PID {pid})", str(clone_path)
        else:
            return True, f"dead (PID {pid})", str(clone_path)

    return True, "no PID file found", str(clone_path)


# ---------------------------------------------------------------------------
# OS-aware terminal spawning
# ---------------------------------------------------------------------------

def _detect_os():
    """Detect OS. Returns 'windows', 'macos', 'linux'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    else:
        return "linux"


def _find_boot_script(clone_root, role):
    """Find the boot script for a role. Returns (path, type) or (None, None).

    Priority (#4966):
    1. Thin launcher (references/scripts/thin_launcher.py) — new default
    2. Legacy wrapper scripts (start-{role}.ps1/.sh) — backward compat
    """
    clone_root = Path(clone_root)
    sqdir = clone_root / ".squidsquad"

    # Prefer thin launcher (#4966) — harness owns lifecycle, no wrapper needed
    thin_launcher = clone_root / "references" / "scripts" / "thin_launcher.py"
    if thin_launcher.exists():
        return thin_launcher, "thin"

    # Legacy fallback: wrapper scripts
    os_type = _detect_os()
    if os_type == "windows":
        ps1 = sqdir / f"start-{role}.ps1"
        if ps1.exists():
            return ps1, "ps1"
        sh = sqdir / f"start-{role}.sh"
        if sh.exists():
            return sh, "sh"
    else:
        sh = sqdir / f"start-{role}.sh"
        if sh.exists():
            return sh, "sh"
        ps1 = sqdir / f"start-{role}.ps1"
        if ps1.exists():
            return ps1, "ps1"

    return None, None


def _spawn_terminal(clone_root, role, boot_script, script_type):
    """Spawn a new terminal window running the boot script. Returns (success, message)."""
    os_type = _detect_os()
    clone_root = Path(clone_root)
    script_path = str(boot_script)

    if os_type == "windows":
        return _spawn_windows(clone_root, role, script_path, script_type)
    elif os_type == "macos":
        return _spawn_macos(clone_root, role, script_path, script_type)
    else:
        return _spawn_linux(clone_root, role, script_path, script_type)


def _spawn_windows(clone_root, role, script_path, script_type):
    """Spawn on Windows using wt.exe or fallback."""
    wt = shutil.which("wt")
    if wt:
        try:
            if script_type == "thin":
                cmd = [wt, "new-tab", "--title", f"squidsquad-{role}",
                       "-d", str(clone_root),
                       "python", script_path, role]
            elif script_type == "ps1":
                cmd = [wt, "new-tab", "--title", f"squidsquad-{role}",
                       "-d", str(clone_root),
                       "pwsh", "-NoExit", "-File", script_path]
            else:
                cmd = [wt, "new-tab", "--title", f"squidsquad-{role}",
                       "-d", str(clone_root),
                       "bash", script_path]
            subprocess.Popen(
                cmd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=str(clone_root),
            )
            launcher = "thin launcher" if script_type == "thin" else "wt.exe"
            return True, f"spawned via {launcher} (Windows Terminal)"
        except Exception as e:
            return False, f"wt.exe spawn failed: {e}"

    # Fallback: cmd /c start
    try:
        if script_type == "thin":
            cmd = ["cmd", "/c", "start", f"squidsquad-{role}",
                   "python", script_path, role]
        elif script_type == "ps1":
            cmd = ["cmd", "/c", "start", f"squidsquad-{role}",
                   "pwsh", "-NoExit", "-File", script_path]
        else:
            cmd = ["cmd", "/c", "start", f"squidsquad-{role}",
                   "bash", script_path]
        subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=str(clone_root),
        )
        return True, "spawned via cmd /c start (fallback)"
    except Exception as e:
        return False, f"Windows fallback spawn failed: {e}"


def _spawn_macos(clone_root, role, script_path, script_type):
    """Spawn on macOS using Terminal.app via osascript.

    Writes the shell command to a temporary .sh file so that AppleScript
    never interpolates path characters (quotes, backslashes).  The temp
    file self-deletes after execution.
    """
    tmp_path = None
    try:
        quoted_root = shlex.quote(str(clone_root))
        quoted_script = shlex.quote(str(script_path))
        if script_type == "thin":
            run_cmd = f"cd {quoted_root} && python {quoted_script} {role}"
        else:
            run_cmd = f"cd {quoted_root} && bash {quoted_script}"

        # Write to a temp .sh file to avoid AppleScript string interpolation
        # issues with paths containing quotes, backslashes, or special chars.
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", prefix="squidsquad-boot-",
            delete=False,
        )
        tmp_path = tmp.name
        tmp.write("#!/bin/bash\n")
        tmp.write(run_cmd + "\n")
        tmp.write(f"rm -f {shlex.quote(tmp_path)}\n")  # self-cleanup
        tmp.close()
        os.chmod(tmp_path, 0o700)

        # Temp path is safe (alphanumeric + hyphens from tempfile module),
        # so no AppleScript escaping needed.
        apple_script = (
            f'tell application "Terminal" to do script '
            f'"bash {tmp_path}"'
        )
        subprocess.Popen(
            ["osascript", "-e", apple_script],
            cwd=str(clone_root),
        )
        launcher = "thin launcher" if script_type == "thin" else "Terminal.app"
        return True, f"spawned via {launcher} (osascript)"
    except Exception as e:
        # Clean up temp file on failure — self-cleanup rm only runs on success.
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False, f"macOS spawn failed: {e}"


def _spawn_linux(clone_root, role, script_path, script_type):
    """Spawn on Linux using tmux."""
    tmux = shutil.which("tmux")
    if tmux:
        try:
            session_name = f"squidsquad-{role}"
            subprocess.run(
                [tmux, "kill-session", "-t", session_name],
                capture_output=True, check=False,
            )
            quoted_root = shlex.quote(str(clone_root))
            quoted_script = shlex.quote(str(script_path))
            if script_type == "thin":
                run_cmd = f"cd {quoted_root} && python {quoted_script} {role}"
            else:
                run_cmd = f"cd {quoted_root} && bash {quoted_script}"
            subprocess.Popen(
                [tmux, "new-session", "-d", "-s", session_name, run_cmd],
                cwd=str(clone_root),
            )
            launcher = "thin launcher" if script_type == "thin" else "tmux"
            return True, f"spawned via {launcher} (tmux session '{session_name}')"
        except Exception as e:
            return False, f"tmux spawn failed: {e}"

    return False, (
        f"No terminal available. Manual boot:\n"
        f"  cd {clone_root} && python {script_path} {role}"
    )


# ---------------------------------------------------------------------------
# Main boot logic
# ---------------------------------------------------------------------------

def boot_agent(role, dry_run=False):
    """Boot a single agent. Returns result dict."""
    result = {
        "role": role,
        "action": "skip",
        "success": False,
        "message": "",
        "timestamp": time.time(),
    }

    # PID-based detection
    needs, reason, clone_path = _needs_boot(role)
    if not needs:
        result["action"] = "skip"
        result["success"] = True
        result["message"] = f"skip: {reason}"
        return result

    # Dry run
    if dry_run:
        result["action"] = "dry-run"
        result["success"] = True
        result["message"] = f"would boot: {reason}"
        return result

    # Boot lock — claim the slot (#3347)
    if not _write_booting_sentinel(clone_path, role):
        result["action"] = "skip"
        result["success"] = True
        result["message"] = "another boot in progress"
        return result

    # Clean stale .restart sentinel (#3349)
    _clean_stale_restart(clone_path, role)

    # Find boot script
    boot_script, script_type = _find_boot_script(clone_path, role)
    if boot_script is None:
        _clear_booting_sentinel(clone_path, role)
        result["message"] = (
            f"no boot script found at {clone_path}/.squidsquad/start-{role}.[sh|ps1]\n"
            f"Manual boot: cd {clone_path} && claude -p .squidsquad/{role}/CLAUDE.md"
        )
        return result

    # Spawn
    success, msg = _spawn_terminal(clone_path, role, boot_script, script_type)
    result["action"] = "spawn"
    result["success"] = success
    result["message"] = msg

    # Clear sentinel on failure (on success, thin_launcher clears it)
    if not success:
        _clear_booting_sentinel(clone_path, role)

    return result


def boot_all(dry_run=False):
    """Boot all agents that need it. Returns list of result dicts."""
    roles = _get_all_roles()
    if not roles:
        return [{"role": "all", "action": "skip", "success": True,
                 "message": "no agents configured"}]

    results = []
    for role in roles:
        r = boot_agent(role, dry_run=dry_run)
        results.append(r)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    use_json = "--json" in args
    dry_run = "--dry-run" in args
    boot_all_flag = "--all" in args
    role = None

    for i, a in enumerate(args):
        if a == "--role" and i + 1 < len(args):
            role = args[i + 1]

    if not boot_all_flag and not role:
        print("Usage: boot_remote.py --role <name> | --all [--dry-run] [--json]",
              file=sys.stderr)
        return 2

    # Check prerequisites
    if not SQUIDSQUAD_DIR.exists():
        print("ERROR: .squidsquad/ not found", file=sys.stderr)
        return 2

    # Run
    if boot_all_flag:
        results = boot_all(dry_run=dry_run)
    else:
        results = [boot_agent(role, dry_run=dry_run)]

    # Output
    if use_json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            print(f"[{r['role']}] {r['action']} — {status}: {r['message']}")

    # Exit code: 1 if any spawn failed
    any_failed = any(
        r["action"] == "spawn" and not r["success"]
        for r in results
    )
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
