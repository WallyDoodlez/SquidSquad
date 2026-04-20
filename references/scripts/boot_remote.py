#!/usr/bin/env python3
"""SquidSquad remote agent boot — spawn dead agents in new terminals.

PM is the bootmaster. Detection uses .health file (primary) with PID fallback:
read each agent's .health file for liveness status. If .health shows dead/error
or is missing, check .pid as fallback. If agent needs booting and no .stop
sentinel, spawn a new terminal. After spawning, polls .health for up to 30s
to confirm the agent started successfully.

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
    """Parse clone paths → {role: Path(clone_root)}.

    Reads from ~/.squidsquad/clones/ first (shared filesystem),
    falls back to .local-config (legacy).
    """
    result = {}

    # Try shared filesystem first
    shared_clones = Path.home() / ".squidsquad" / "clones"
    if shared_clones.exists() and shared_clones.is_dir():
        for clone_file in shared_clones.iterdir():
            if clone_file.is_file() and not clone_file.name.startswith("."):
                try:
                    path = clone_file.read_text(encoding="utf-8").strip()
                    if path:
                        result[clone_file.name] = Path(path)
                except (OSError, UnicodeDecodeError):
                    continue
        if result:
            return result

    # Fall back to .local-config (legacy format: `- **role**: /absolute/path`)
    if not LOCAL_CONFIG.exists():
        return {}
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
    """Get all agent roles from config.md only. Excludes 'pm' (bootmaster).

    Only reads the Dev Agents list from config.md — does not scan directories
    or .local-config for extra roles. This prevents booting agents that have
    been removed from config.md but still have leftover directories (#943).
    """
    roles = set(_parse_dev_agents())
    # Also check for coordination roles listed in config (DM, QA, Designer sections)
    if CONFIG_MD.exists():
        try:
            text = CONFIG_MD.read_text(encoding="utf-8")
            # DM: present if "DM**: present" in config
            if re.search(r"\*\*DM\*\*:\s*present", text, re.IGNORECASE):
                roles.add("dm")
            # QA: present if listed in Dev Agents or "QA**: always present"
            if re.search(r"\*\*QA\*\*:\s*always present", text, re.IGNORECASE):
                roles.add("qa")
        except Exception:
            pass
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




def _read_health_file(clone_path, role):
    """Read .health file for a role. Returns (status, detail) or (None, None)."""
    health_file = Path(clone_path) / ".squidsquad" / role / ".health"
    if not health_file.exists():
        return None, None
    try:
        content = health_file.read_text(encoding="utf-8").strip()
        if not content:
            return None, None
        parts = content.split("|", 1)
        status = parts[0].strip()
        detail = parts[1].strip() if len(parts) > 1 else ""
        return status, detail
    except (OSError, UnicodeDecodeError):
        return None, None


def _needs_boot(role):
    """Determine if an agent needs booting.

    Uses .health file (primary) with PID fallback.
    Returns (needs_boot, reason, clone_path).
    Context pressure restarts are handled by each agent's boot script, not here.
    """
    clone_path = _get_clone_path(role)

    # Check .stop sentinel first
    if _has_stop_sentinel(clone_path, role):
        return False, "explicitly stopped (.stop sentinel)", str(clone_path)

    # Primary: check .health file
    health_status, health_detail = _read_health_file(clone_path, role)
    if health_status is not None:
        if health_status in ("alive", "booting", "restarting"):
            return False, f".health={health_status} (agent running)", str(clone_path)
        elif health_status == "dead":
            return True, ".health=dead (wrapper exited)", str(clone_path)
        elif health_status == "error":
            detail_msg = f": {health_detail}" if health_detail else ""
            return True, f".health=error{detail_msg}", str(clone_path)
        elif health_status == "backoff":
            # Agent is in crash loop — wrapper is still running, don't double-boot
            return False, ".health=backoff (wrapper handling restarts)", str(clone_path)

    # Fallback: check PID (old boot scripts without .health)
    pid = _read_pid_file(clone_path, role)
    if pid is None:
        return True, "no .health file, no PID file (agent not running)", str(clone_path)

    if not _is_process_alive(pid):
        return True, f"no .health file, process dead (PID {pid} not found)", str(clone_path)

    return False, f"no .health file, process alive (PID {pid})", str(clone_path)


def _poll_health_after_spawn(clone_path, role, timeout=30):
    """Poll .health file after spawning, waiting for 'alive' status.

    Returns (confirmed, final_status, message).
    """
    poll_interval = 2
    elapsed = 0
    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        health_status, health_detail = _read_health_file(clone_path, role)
        if health_status == "alive":
            return True, "alive", f"agent confirmed alive after {elapsed}s"
        elif health_status == "error":
            detail_msg = f": {health_detail}" if health_detail else ""
            return False, "error", f"agent boot failed{detail_msg}"
    # Timeout — check what we have
    health_status, _ = _read_health_file(clone_path, role)
    if health_status == "booting":
        return True, "booting", f"agent still booting after {timeout}s (health unconfirmed)"
    return True, health_status or "unknown", f"health poll timed out after {timeout}s"


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
    """Acquire boot-lock atomically. Returns True if acquired."""
    try:
        if BOOT_LOCK.exists():
            mtime = BOOT_LOCK.stat().st_mtime
            if time.time() - mtime < LOCK_TTL_SECONDS:
                return False
            BOOT_LOCK.unlink(missing_ok=True)
        # Atomic create — O_CREAT | O_EXCL fails if file already exists
        fd = os.open(str(BOOT_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
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

        # Post-spawn: poll .health for confirmation (30s timeout)
        if success and not dry_run:
            confirmed, health_status, poll_msg = _poll_health_after_spawn(
                clone_path, role, timeout=30
            )
            result["health_confirmed"] = confirmed
            result["health_status"] = health_status
            result["message"] = f"{msg} — {poll_msg}"
            if not confirmed:
                result["success"] = False
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
