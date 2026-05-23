#!/usr/bin/env python3
"""SquidSquad remote agent boot — spawn dead agents in new terminals.

Spawns agents via thin launcher (primary) or legacy wrapper scripts (fallback).
Liveness is detected exclusively via `.claude-pid` (written by the thin
launcher) — the harness calls boot_agent() for auto-reboot; start_team.py
calls it for manual boot. The legacy `.pid` / `.health` / `.stop` /
`.restart` sentinel reads were removed under #4792 (CONTEXT-4792.md §5.2);
agent lifecycle is owned by harness intent state.

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

sys.path.insert(0, str(SCRIPT_DIR))
from process_utils import is_process_alive as _is_process_alive  # noqa: E402  (#8891)

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
            m = re.match(r"-\s*\*\*([\w-]+)\*\*:\s*(.+)", line)
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


def _parse_workers():
    """Read Workers list from config.md → list of role names.

    #6274 D2: reads the canonical post-rename field `Workers:` first,
    then falls back to the deprecated `Dev Agents:` field. After 6274.3
    the legacy regex is removed.
    """
    if not CONFIG_MD.exists():
        return []
    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        # Try the new canonical field first.
        m = re.search(r"Workers\*\*:\s*(.+)", text)
        if m:
            return [a.strip() for a in m.group(1).split(",") if a.strip()]
        # Fall back to the deprecated `Dev Agents:` field. No warning here —
        # `config.get_field('workers')` emits the canonical one once at the
        # central read site; emitting again here would double-log.
        m = re.search(r"Dev Agents\*\*:\s*(.+)", text)
        if m:
            return [a.strip() for a in m.group(1).split(",") if a.strip()]
    except Exception:
        pass
    return []


# #6274 D2 backward-compat alias. Existing callers that import
# `_parse_dev_agents` continue to work through the dual-aware window.
# Deleted in 6274.3.
def _parse_dev_agents():
    """Deprecated alias for `_parse_workers` — kept through #6274 cutover."""
    return _parse_workers()


def _get_all_roles():
    """Get all agent roles from config.md, including PM.

    Only reads the Workers list from config.md — does not scan directories
    or .local-config for extra roles. This prevents booting agents that have
    been removed from config.md but still have leftover directories (#943).

    #6274 D2: calls `_parse_dev_agents` (the backward-compat alias) rather
    than `_parse_workers` directly so existing tests that `@patch
    boot_remote._parse_dev_agents` continue to work. In 6274.3 the alias
    is deleted and this line switches to `_parse_workers()`.
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

# _has_stop_sentinel / _read_pid_file / _read_health_file / _clean_stale_restart
# were all removed in #4792 (CONTEXT-4792.md \u00a75.2). Agent lifecycle is now
# controlled entirely by harness state (intent=running/stopping/restarting/
# stopped); the legacy sentinel files caused split-brain when removing them
# in the primary repo didn't affect clones, and when stale sentinels silently
# overrode harness intent. Liveness is read exclusively from `.claude-pid`.


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
    """Atomically claim the boot slot for a role.

    #9941: the original implementation used a check-then-rename pattern
    (``_has_booting_sentinel`` False → ``tmp.write_text`` → ``tmp.replace``)
    which is NOT atomic at the slot-claim level. Two concurrent invocations
    could both pass the check, both write a tmp, both ``replace``, and both
    return True — falsely claiming a slot they shouldn't share. ``Path.replace``
    overwrites silently; only the downstream ``thin_launcher`` singleton
    (#8879) defused the actual double-boot in practice.

    The fix is ``os.open`` with ``O_CREAT | O_EXCL``: the OS atomically
    creates the file IFF it doesn't exist, otherwise raises ``FileExistsError``.
    This makes the slot claim truly atomic with no possibility of two
    callers winning.

    Returns ``True`` if we got the slot, ``False`` if another boot is
    already in progress OR a stale sentinel still occupies the path
    (caller can clean stale sentinels via ``_has_booting_sentinel``'s
    TTL-aware path, which fires before this function on a normal retry).
    """
    squid_dir = Path(clone_path) / ".squidsquad" / role
    booting_file = squid_dir / ".booting"

    # Best-effort stale cleanup: _has_booting_sentinel deletes its own
    # stale sentinel as a side effect when age > BOOTING_SENTINEL_TTL.
    # Calling it here keeps the prior recovery behavior — without this,
    # a stale sentinel would block all future boots until manually removed.
    if _has_booting_sentinel(clone_path, role):
        return False

    try:
        squid_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    # Atomic create-or-fail (#9941). O_EXCL is honored on POSIX and on
    # Windows under Python 3.3+ (CreateFileW with CREATE_NEW disposition).
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(booting_file), flags, 0o644)
    except FileExistsError:
        # Another boot already claimed the slot between the TTL check
        # above and this call (or claimed it concurrently). Not our slot.
        return False
    except OSError:
        return False

    # File created; we own the slot. Write the PID for diagnostic readers
    # (orphan_cleanup logs / operator forensics) and close. If the write
    # itself fails, unlink the sentinel so a retry can proceed — leaving
    # an empty sentinel would block future boots until TTL expiry.
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True
    except OSError:
        try:
            booting_file.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _clear_booting_sentinel(clone_path, role):
    """Remove .booting sentinel after boot completes or fails."""
    booting_file = Path(clone_path) / ".squidsquad" / role / ".booting"
    try:
        booting_file.unlink(missing_ok=True)
    except OSError:
        pass


def _needs_boot(role):
    """Determine if an agent needs booting.

    Checks (in order): `.booting` lock, then `.claude-pid` for liveness.
    Returns (needs_boot, reason, clone_path).

    #4792: legacy `.stop` / `.health` / `.pid` sentinel checks removed.
    Stop intent lives in harness state; `.claude-pid` (written by
    `thin_launcher`) is the sole liveness signal. Auto-reboot honors
    `intent` (`stopping`/`stopped` blocks reboot).
    """
    clone_path = _get_clone_path(role)

    # .booting sentinel — another boot is already in progress
    if _has_booting_sentinel(clone_path, role):
        return False, "boot already in progress", str(clone_path)

    # `.claude-pid` is the sole liveness signal (#4966 + #4792)
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    corrupt = False
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if _is_process_alive(pid):
                return False, f"alive (PID {pid})", str(clone_path)
            else:
                return True, f"dead (PID {pid})", str(clone_path)
        except (ValueError, OSError) as e:
            print(f"WARNING: corrupt .claude-pid for {role}: {e}", file=sys.stderr)
            corrupt = True

    # Distinguish "file is corrupt" from "no file at all" — operators reading
    # the boot result message benefit from knowing the file exists but is
    # unreadable rather than chasing a missing-file diagnosis.
    reason = "corrupt .claude-pid" if corrupt else "no PID file found"
    return True, reason, str(clone_path)


# ---------------------------------------------------------------------------
# OS-aware terminal spawning
# ---------------------------------------------------------------------------

def _detect_os():
    """Detect OS. Returns 'windows', 'macos', 'linux'.

    Uses ``sys.platform`` (compile-time constant) rather than
    ``platform.system()`` — the latter calls ``platform.uname()`` which
    on Python 3.12 Windows triggers a WMI query that can hang and wedge
    the harness (#9903).
    """
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
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
    """Spawn a new terminal window running the boot script. Returns (success, message, terminal_pid)."""
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
    """Spawn on Windows using wt.exe or fallback. Returns (success, message, terminal_pid)."""
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
            proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=str(clone_root),
            )
            launcher = "thin launcher" if script_type == "thin" else "wt.exe"
            # wt.exe exits after creating the tab — proc.pid is short-lived (#7630 P-5)
            return True, f"spawned via {launcher} (Windows Terminal)", proc.pid
        except Exception as e:
            return False, f"wt.exe spawn failed: {e}", None

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
        proc = subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=str(clone_root),
        )
        return True, "spawned via cmd /c start (fallback)", proc.pid
    except Exception as e:
        return False, f"Windows fallback spawn failed: {e}", None


def _spawn_macos(clone_root, role, script_path, script_type):
    """Spawn on macOS using Terminal.app via osascript. Returns (success, message, terminal_pid)."""
    tmp_path = None
    try:
        quoted_root = shlex.quote(str(clone_root))
        quoted_script = shlex.quote(str(script_path))
        if script_type == "thin":
            run_cmd = f"cd {quoted_root} && python {quoted_script} {role}"
        else:
            run_cmd = f"cd {quoted_root} && bash {quoted_script}"

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", prefix="squidsquad-boot-",
            delete=False,
        )
        tmp_path = tmp.name
        tmp.write("#!/bin/bash\n")
        tmp.write(run_cmd + "\n")
        tmp.write(f"rm -f {shlex.quote(tmp_path)}\n")
        tmp.close()
        os.chmod(tmp_path, 0o700)

        apple_script = (
            f'tell application "Terminal" to do script '
            f'"bash {tmp_path}"'
        )
        proc = subprocess.Popen(
            ["osascript", "-e", apple_script],
            cwd=str(clone_root),
        )
        launcher = "thin launcher" if script_type == "thin" else "Terminal.app"
        # osascript PID — indirect reference to Terminal.app (#7630 P-5)
        return True, f"spawned via {launcher} (osascript)", proc.pid
    except Exception as e:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False, f"macOS spawn failed: {e}", None


def _spawn_linux(clone_root, role, script_path, script_type):
    """Spawn on Linux using tmux. Returns (success, message, terminal_pid)."""
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
            proc = subprocess.Popen(
                [tmux, "new-session", "-d", "-s", session_name, run_cmd],
                cwd=str(clone_root),
            )
            launcher = "thin launcher" if script_type == "thin" else "tmux"
            # tmux new-session exits after creating the detached session — proc.pid is short-lived (#7630 P-5)
            return True, f"spawned via {launcher} (tmux session '{session_name}')", proc.pid
        except Exception as e:
            return False, f"tmux spawn failed: {e}", None

    return False, (
        f"No terminal available. Manual boot:\n"
        f"  cd {clone_root} && python {script_path} {role}"
    ), None


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

    # #9688 / CONTEXT-9688 D2: sweep orphan claude.exe subagents BEFORE
    # spawning the new agent. Boot is a natural cleanup window — the role
    # we're about to spawn is by definition not yet in .claude-pid (or
    # holds the OLD cmd.exe PID we're replacing), so any claude.exe child
    # of that old PID is unambiguously stale. Skip-if-any-role-unresolved
    # (D3) protects sibling roles during this window.
    if not dry_run:
        try:
            import orphan_cleanup
            orphan_cleanup.sweep(invoked_by=f"boot_remote:{role}")
        except (ImportError, Exception):
            # Best-effort — boot must proceed even if cleanup is unavailable.
            pass

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

    # #4792: stale `.restart` sentinel cleanup deleted with _clean_stale_restart.
    # Restart intent now lives exclusively in harness state.

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
    success, msg, terminal_pid = _spawn_terminal(clone_path, role, boot_script, script_type)
    result["action"] = "spawn"
    result["success"] = success
    result["message"] = msg
    result["terminal_pid"] = terminal_pid

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
