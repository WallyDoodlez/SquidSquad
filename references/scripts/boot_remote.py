#!/usr/bin/env python3
"""SquidSquad remote agent boot — spawn dead agents in new terminals.

PM is the bootmaster. Detection is PID-based: read each agent's .pid file,
check if the process is alive. If dead (or no PID file) and no .stop sentinel,
spawn a new terminal.

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
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
LOCAL_CONFIG = SQUIDSQUAD_DIR / ".local-config"
CONFIG_MD = SQUIDSQUAD_DIR / "config.md"
BOOT_LOG = SQUIDSQUAD_DIR / "boot-attempts.log"
BOOT_LOCK = SQUIDSQUAD_DIR / "boot-lock"

COOLDOWN_SECONDS = 600  # 10 minutes between spawn attempts per role
LOCK_TTL_SECONDS = 30


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def _parse_local_config():
    """Parse .local-config → {role: Path(clone_root)}.

    Format: `- **role**: /absolute/path`
    Returns empty dict if file missing.
    """
    if not LOCAL_CONFIG.exists():
        return {}
    result = {}
    try:
        text = LOCAL_CONFIG.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"-\s*\*\*(\w+)\*\*:\s*(.+)", line)
            if m:
                role = m.group(1).strip()
                path = Path(m.group(2).strip())
                result[role] = path
    except Exception:
        pass
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
    """Get all agent roles from config + local-config. Excludes 'pm' (bootmaster)."""
    roles = set()
    # From config.md Dev Agents
    roles.update(_parse_dev_agents())
    # From .local-config
    roles.update(_parse_local_config().keys())
    # Add known coordination roles
    for role in ("dm", "qa", "designer"):
        role_dir = SQUIDSQUAD_DIR / role
        if role_dir.exists():
            roles.add(role)
    roles.discard("pm")  # PM is the bootmaster, never boots itself
    return sorted(roles)


def _get_clone_path(role):
    """Get the clone root path for a role. Falls back to REPO_ROOT."""
    local = _parse_local_config()
    return local.get(role, REPO_ROOT)


# ---------------------------------------------------------------------------
# PID-based process detection
# ---------------------------------------------------------------------------

def _read_pid_file(clone_path, role):
    """Read PID from .squidsquad/{role}/.pid. Returns int or None."""
    pid_file = Path(clone_path) / ".squidsquad" / role / ".pid"
    if not pid_file.exists():
        return None
    try:
        content = pid_file.read_text(encoding="utf-8").strip()
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




def _needs_boot(role):
    """Determine if an agent needs booting based on PID.

    Returns (needs_boot, reason, clone_path).
    Context pressure restarts are handled by each agent's boot script, not here.
    """
    clone_path = _get_clone_path(role)

    # Check .stop sentinel first
    if _has_stop_sentinel(clone_path, role):
        return False, "explicitly stopped (.stop sentinel)", str(clone_path)

    # Check PID
    pid = _read_pid_file(clone_path, role)
    if pid is None:
        return True, "no PID file (agent not running)", str(clone_path)

    if not _is_process_alive(pid):
        return True, f"process dead (PID {pid} not found)", str(clone_path)

    return False, f"process alive (PID {pid})", str(clone_path)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def _read_boot_log():
    """Read boot-attempts.log → list of dicts."""
    if not BOOT_LOG.exists():
        return []
    try:
        lines = BOOT_LOG.read_text(encoding="utf-8").strip().splitlines()
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except Exception:
        return []


def _append_boot_log(entry):
    """Append a JSON line to boot-attempts.log."""
    try:
        with open(BOOT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _check_cooldown(role):
    """Check if role is in cooldown. Returns (in_cooldown, seconds_remaining)."""
    now = time.time()
    entries = _read_boot_log()
    for entry in reversed(entries):
        if entry.get("role") == role and entry.get("action") == "spawn":
            elapsed = now - entry.get("timestamp", 0)
            if elapsed < COOLDOWN_SECONDS:
                return True, int(COOLDOWN_SECONDS - elapsed)
    return False, 0


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------

def _acquire_lock():
    """Acquire boot-lock. Returns True if acquired."""
    try:
        if BOOT_LOCK.exists():
            mtime = BOOT_LOCK.stat().st_mtime
            if time.time() - mtime < LOCK_TTL_SECONDS:
                return False
            BOOT_LOCK.unlink(missing_ok=True)
        BOOT_LOCK.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except Exception:
        return False


def _release_lock():
    """Release boot-lock."""
    try:
        BOOT_LOCK.unlink(missing_ok=True)
    except Exception:
        pass


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
    """Find the boot script for a role. Returns (path, type) or (None, None)."""
    clone_root = Path(clone_root)
    sqdir = clone_root / ".squidsquad"

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
            if script_type == "ps1":
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
            return True, "spawned via wt.exe (Windows Terminal)"
        except Exception as e:
            return False, f"wt.exe spawn failed: {e}"

    # Fallback: cmd /c start
    try:
        if script_type == "ps1":
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
    """Spawn on macOS using Terminal.app via osascript."""
    try:
        quoted_root = shlex.quote(str(clone_root))
        quoted_script = shlex.quote(str(script_path))
        apple_script = (
            f'tell application "Terminal" to do script '
            f'"cd {quoted_root} && bash {quoted_script}"'
        )
        subprocess.Popen(
            ["osascript", "-e", apple_script],
            cwd=str(clone_root),
        )
        return True, "spawned via Terminal.app (osascript)"
    except Exception as e:
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
            subprocess.Popen(
                [tmux, "new-session", "-d", "-s", session_name,
                 f"cd {quoted_root} && bash {quoted_script}"],
                cwd=str(clone_root),
            )
            return True, f"spawned via tmux session '{session_name}'"
        except Exception as e:
            return False, f"tmux spawn failed: {e}"

    return False, (
        f"No terminal available. Manual boot:\n"
        f"  cd {clone_root} && bash {script_path}"
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

    # Check cooldown
    in_cooldown, remaining = _check_cooldown(role)
    if in_cooldown:
        result["action"] = "skip"
        result["success"] = True
        result["message"] = f"cooldown active ({remaining}s remaining), skipping"
        return result

    # Dry run
    if dry_run:
        result["action"] = "dry-run"
        result["success"] = True
        result["message"] = f"would boot: {reason}"
        return result

    # Find boot script
    boot_script, script_type = _find_boot_script(clone_path, role)
    if boot_script is None:
        result["message"] = (
            f"no boot script found at {clone_path}/.squidsquad/start-{role}.[sh|ps1]\n"
            f"Manual boot: cd {clone_path} && claude -p .squidsquad/{role}/CLAUDE.md"
        )
        return result

    # Acquire lock
    if not _acquire_lock():
        result["message"] = "boot-lock held by another process, skipping"
        result["action"] = "skip"
        result["success"] = True
        return result

    try:
        # Spawn
        success, msg = _spawn_terminal(clone_path, role, boot_script, script_type)
        result["action"] = "spawn"
        result["success"] = success
        result["message"] = msg

        # Log attempt
        _append_boot_log({
            "timestamp": time.time(),
            "role": role,
            "action": "spawn",
            "success": success,
            "message": msg,
            "reason": reason,
        })
    finally:
        _release_lock()

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

    # Check if auto-boot is enabled
    try:
        config_text = CONFIG_MD.read_text(encoding="utf-8")
        m = re.search(r"Auto Boot.*?:\s*(yes|no)", config_text, re.IGNORECASE)
        if m and m.group(1).lower() == "no":
            msg = "Auto Boot Agents disabled in config.md"
            if use_json:
                print(json.dumps({"action": "disabled", "message": msg}))
            else:
                print(msg)
            return 0
    except Exception:
        pass

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
