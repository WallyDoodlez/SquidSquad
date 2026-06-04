#!/usr/bin/env python3
"""SquidSquad CLI — thin client for the harness HTTP API.

Cross-platform Python CLI that communicates with the SquidSquad harness.
Discovers the harness port via .squidsquad/.harness-port.

Usage:
    python squidsquad_cli.py start              # Boot harness + all agents
    python squidsquad_cli.py start <role>       # Boot harness + one agent
    python squidsquad_cli.py stop               # Stop all agents
    python squidsquad_cli.py stop <role>         # Stop one agent
    python squidsquad_cli.py restart <role>      # Restart one agent
    python squidsquad_cli.py status             # Show harness + agent health
    python squidsquad_cli.py shutdown           # Stop all agents + exit harness

Exit codes:
    0 — success
    1 — error (harness not running, API failure)
    2 — usage error
"""

import io
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Ensure stdout can handle Unicode emoji on Windows (cp1252 can't encode them)
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"
HARNESS_SCRIPT = SCRIPT_DIR / "harness.py"

HARNESS_STARTUP_TIMEOUT = 15  # seconds to wait for harness to start
API_TIMEOUT = 10  # seconds for individual API calls


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

def _read_port() -> int | None:
    """Read the harness port from the discovery file. Returns None if missing."""
    if not HARNESS_PORT_FILE.exists():
        return None
    try:
        content = HARNESS_PORT_FILE.read_text(encoding="utf-8").strip()
        return int(content) if content else None
    except (ValueError, OSError):
        return None


def _harness_alive(port: int) -> bool:
    """Ping the harness /status endpoint. Returns True if responsive."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _discover_harness() -> int | None:
    """Discover a running harness. Returns port or None.

    Reads .harness-port and pings /status. If the port file exists but the
    harness doesn't respond (stale crash remnant), returns None.
    """
    port = _read_port()
    if port is None:
        return None
    if _harness_alive(port):
        return port
    return None


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

class HarnessAPIError(Exception):
    """Transport- or HTTP-level failure talking to the harness API.

    `_api_call` raises this instead of `sys.exit(1)` so per-role aggregation
    loops in the operator commands and the `start_team.py` shim can catch +
    continue, producing complete aggregation across all targeted roles even
    when one role fails at the transport layer (#4792 §5.7).
    """


def _api_call(port: int, method: str, path: str) -> dict:
    """Make an HTTP call to the harness API. Returns parsed JSON.

    Raises `HarnessAPIError` on transport or HTTP failure — the caller is
    expected to catch and translate to a failure result for aggregation.
    Stderr still receives the diagnostic message so operators see it.
    """
    url = f"http://localhost:{port}{path}"
    req = urllib.request.Request(url, method=method)

    # POST requires content-length header even with no body
    if method == "POST":
        req.add_header("Content-Type", "application/json")
        req.data = b""

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, AttributeError):
            detail = body
        print(f"Error: {e.code} — {detail}", file=sys.stderr)
        raise HarnessAPIError(f"HTTP {e.code}: {detail}")
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"Harness not running or unreachable: {e}. Start with: squidsquad start",
              file=sys.stderr)
        raise HarnessAPIError(f"transport error: {e}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_start(role: str | None = None):
    """Boot harness (if not running) + start agent(s).

    When `role` is None, starts all agents via `/agents/all/start`. When `role`
    is given, starts that agent only via `/agents/{role}/start`. In both cases
    the harness is spawned first if it is not already running.
    """
    port = _discover_harness()

    if port is None:
        # Spawn harness in a new terminal window
        print("Starting harness...")
        port = _spawn_harness()
        if port is None:
            print("Failed to start harness.", file=sys.stderr)
            return 1

    if role:
        print(f"Starting {role} (harness on port {port})...")
        try:
            result = _api_call(port, "POST", f"/agents/{role}/start")
        except HarnessAPIError:
            print(f"  [{role}] FAIL: harness API error (see stderr)")
            return 1
        success = result.get("success", False)
        action = result.get("action", "?")
        message = result.get("message", "")
        print(f"  [{role}] {action} — {'OK' if success else 'FAIL'}: {message}")
        return 0 if success else 1

    # Start all agents via harness
    print(f"Starting all agents (harness on port {port})...")
    try:
        result = _api_call(port, "POST", "/agents/all/start")
    except HarnessAPIError:
        return 1

    # Print results and aggregate success across agents.
    results = result.get("results", [])
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        print(f"  [{r.get('role', '?')}] {r.get('action', '?')} — {status}: {r.get('message', '')}")

    all_ok = bool(results) and all(r.get("success", False) for r in results)
    return 0 if all_ok else 1


def cmd_stop(role: str | None = None):
    """Stop agent(s).

    Returns 0 only when every targeted agent reports `success: true` from the
    harness API; non-zero on any failure. The start_team shim's exit code
    propagation depends on this contract.
    """
    port = _discover_harness()
    if port is None:
        print("Harness not running. Start with: squidsquad start", file=sys.stderr)
        return 1

    if role:
        try:
            result = _api_call(port, "POST", f"/agents/{role}/stop")
        except HarnessAPIError:
            print(f"  [{role}] FAIL: harness API error (see stderr)")
            return 1
        success = result.get("success", False)
        message = result.get("message", "stopped" if success else "failed")
        print(f"  [{role}] {'OK' if success else 'FAIL'}: {message}")
        return 0 if success else 1

    try:
        result = _api_call(port, "POST", "/agents/all/stop")
    except HarnessAPIError:
        return 1
    results = result.get("results", [])
    if not results:
        # #10006: nothing to stop is a no-op success, matching cmd_status's
        # treatment of the empty-agents case. Same wording as cmd_status
        # so operators grepping logs / writing shell predicates see one
        # string for "no agents are registered with the harness." Without
        # this, defensive teardown scripts (`squidsquad stop && next-step`)
        # saw exit 1 when the squad was already idle.
        print("No agents detected.")
        return 0
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        print(f"  [{r.get('role', '?')}] {status}")
    return 0 if all(r.get("success", False) for r in results) else 1


def cmd_restart(role: str):
    """Restart a single agent."""
    port = _discover_harness()
    if port is None:
        print("Harness not running. Start with: squidsquad start", file=sys.stderr)
        return 1

    print(f"Restarting {role}...")
    try:
        result = _api_call(port, "POST", f"/agents/{role}/restart")
    except HarnessAPIError:
        print(f"  [{role}] FAIL: harness API error (see stderr)")
        return 1
    success = result.get("success", False)
    print(f"  [{role}] {'OK' if success else 'FAIL'}: {result.get('message', '')}")
    return 0 if success else 1


def cmd_status():
    """Show harness + agent health."""
    port = _discover_harness()
    if port is None:
        print("Harness not running. Start with: squidsquad start", file=sys.stderr)
        return 1

    try:
        result = _api_call(port, "GET", "/status")
    except HarnessAPIError:
        return 1

    # Print harness info
    harness = result.get("harness", {})
    print(f"Harness: {harness.get('status', 'unknown')} (port {harness.get('port', '?')}, uptime {harness.get('uptime_human', '?')})")
    print()

    # Print agent table
    agents = result.get("agents", [])
    if not agents:
        print("No agents detected.")
        return 0

    # Status emoji mapping
    status_emoji = {
        "running": "🦑",
        "starting": "⏳",
        "stopped": "⏹️",
        "stalled": "👻",
        "error": "❌",
        "unknown": "❓",
    }

    w = max(len(a.get("role", "")) for a in agents)
    w = max(w, 5)
    print(f"{'Agent':<{w}}  Status")
    print(f"{'-' * w}  {'-' * 10}")

    for a in agents:
        role = a.get("role", "?")
        status = a.get("status", "unknown")
        emoji = status_emoji.get(status, "❓")
        print(f"{role:<{w}}  {emoji} {status}")

    return 0


def cmd_shutdown():
    """Stop all agents and exit harness."""
    port = _discover_harness()
    if port is None:
        print("Harness not running.", file=sys.stderr)
        return 0  # Nothing to shut down

    print("Shutting down harness and all agents...")
    try:
        result = _api_call(port, "POST", "/shutdown")
        print(result.get("message", "Shutdown complete."))
    except HarnessAPIError:
        # Connection error here typically means the harness closed the socket
        # mid-request as part of the shutdown — treat as success.
        print("Harness shutting down...")

    return 0


# ---------------------------------------------------------------------------
# Harness spawning
# ---------------------------------------------------------------------------

def _spawn_harness() -> int | None:
    """Spawn the harness in a new terminal window. Returns port or None."""
    if not HARNESS_SCRIPT.exists():
        print(f"ERROR: harness.py not found at {HARNESS_SCRIPT}", file=sys.stderr)
        return None

    # sys.platform is a compile-time constant; platform.system() triggers
    # a Python 3.12 Windows WMI wedge that can hang for many seconds (#9903).
    if sys.platform == "win32":
        system = "windows"
    elif sys.platform == "darwin":
        system = "darwin"
    else:
        system = "linux"

    if system == "windows":
        wt = shutil.which("wt")
        if wt:
            try:
                subprocess.Popen(
                    [wt, "new-tab", "--title", "squidsquad-harness",
                     "-d", str(REPO_ROOT),
                     "python", str(HARNESS_SCRIPT)],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(REPO_ROOT),
                )
            except Exception as e:
                print(f"Failed to spawn via wt.exe: {e}", file=sys.stderr)
                return None
        else:
            # Fallback: cmd /c start
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "squidsquad-harness",
                     "python", str(HARNESS_SCRIPT)],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(REPO_ROOT),
                )
            except Exception as e:
                print(f"Failed to spawn harness: {e}", file=sys.stderr)
                return None

    elif system == "darwin":
        try:
            import shlex
            apple_script = (
                f'tell application "Terminal" to do script '
                f'"cd {shlex.quote(str(REPO_ROOT))} && python {shlex.quote(str(HARNESS_SCRIPT))}"'
            )
            subprocess.Popen(["osascript", "-e", apple_script])
        except Exception as e:
            print(f"Failed to spawn harness: {e}", file=sys.stderr)
            return None

    else:  # Linux
        tmux = shutil.which("tmux")
        if tmux:
            try:
                subprocess.run([tmux, "kill-session", "-t", "squidsquad-harness"],
                               capture_output=True, check=False)
                import shlex
                subprocess.Popen(
                    [tmux, "new-session", "-d", "-s", "squidsquad-harness",
                     f"cd {shlex.quote(str(REPO_ROOT))} && python {shlex.quote(str(HARNESS_SCRIPT))}"],
                )
            except Exception as e:
                print(f"Failed to spawn harness via tmux: {e}", file=sys.stderr)
                return None
        else:
            print("No terminal available (need wt.exe, Terminal.app, or tmux).", file=sys.stderr)
            return None

    # Poll for harness startup
    print("Waiting for harness to start...", end="", flush=True)
    for _ in range(HARNESS_STARTUP_TIMEOUT):
        time.sleep(1)
        print(".", end="", flush=True)
        port = _read_port()
        if port and _harness_alive(port):
            print(f" ready (port {port})")
            return port

    print(" timeout", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

USAGE = """\
Usage: squidsquad <command> [args]

Commands:
  start [<role>]     Boot harness + spawn agent(s) — all if no role given
  stop [<role>]      Stop all agents (or one agent)
  restart <role>     Restart a single agent
  status             Show harness + agent health
  shutdown           Stop all agents and exit harness
  check [--full]     Diagnose compose freshness (read-only — no spawn,
                     no mutation). --full is deprecated post-E6 (#10685
                     Phase 3d.3): accepted for backward compat but no
                     longer runs `compose.py deploy-all --check` (that
                     CLI command was retired with the v1 chain).

Examples:
  squidsquad start
  squidsquad restart skill
  squidsquad status
  squidsquad check
  squidsquad check --full
  squidsquad shutdown
"""


# PRD-E E4 (#10683): operator-driven freshness diagnostic. Pure read-
# only — never spawns agents, never mutates state, never runs
# ``compose.py deploy-all`` (only the ``--check`` dry-run when
# ``--full`` is passed).
#
# Exit codes per AC5:
#   0 — clean (no drift, sources compose cleanly)
#   1 — drift detected (structured report on stderr)
#   2 — error (couldn't read sources, malformed config, compose
#       dry-run errored)
_STATE_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / ".squidsquad" / ".harness-state.json"
)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_state_checksum(state_file=_STATE_FILE):
    """Return ``(stored_checksum_or_None, error_message_or_None)``.

    The checksum can be ``None`` when:
    - state file does not exist (fresh install, never booted),
    - state file exists but has no ``last_compose_checksum`` field
      (legacy file, pre-E2).

    Both cases are normal "first boot" states the operator should be
    informed about — not exit-2 errors. A malformed JSON file IS an
    exit-2 error.
    """
    if not state_file.is_file():
        return None, None
    try:
        raw = state_file.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"could not read {state_file}: {e}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"malformed JSON in {state_file}: {e}"
    return data.get("last_compose_checksum"), None


def _enumerate_drifted_paths(repo_root):
    """Return the sorted list of compose-input paths that exist on
    disk today. Used by the drift report so the operator can see what
    the gate would hash; pinpointing WHICH files changed requires
    keeping the prior file-by-file hash list, which today's state file
    does not store. AC6 asks for a "human-readable summary" — listing
    the input set + the current checksum is the honest answer until a
    future story adds a per-file manifest.

    Per DS-10683 F2: uses ``compose_freshness.iter_compose_input_files``
    (public API) and returns ``None`` on enumeration failure so the
    drift report can render a clean fallback line instead of crashing.
    """
    try:
        import compose_freshness as _cf  # lazy — avoid module import on usage-only paths
        paths = []
        for path in _cf.iter_compose_input_files(repo_root):
            try:
                rel = path.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            if rel not in paths:
                paths.append(rel)
        return sorted(paths)
    except Exception:  # noqa: BLE001 — operator-facing fallback
        return None


def _format_drift_report(stored, current, repo_root):
    """Render the AC6 drift report for stderr."""
    lines = [
        "compose freshness: DRIFT DETECTED",
        "",
        f"  stored checksum (.harness-state.json): {stored}",
        f"  current checksum (live source tree):   {current}",
        "",
        (
            "  The compose-input set has changed since the last "
            "successful boot. Run `python references/scripts/"
            "compose.py deploy-all` to bring composed outputs back in "
            "sync. To diagnose WHICH files changed, compare git diff "
            "against the boot point that wrote the stored checksum."
        ),
        "",
        "  Compose-input set (current files on disk):",
    ]
    paths = _enumerate_drifted_paths(repo_root)
    if paths is None:
        # DS-10683 F2 fallback: enumeration failed (private API
        # broke, filesystem permission error, etc.). Report it so
        # the operator sees the drift summary anyway.
        lines.append(
            "    (could not enumerate compose-input files — see "
            "compose_freshness.iter_compose_input_files)"
        )
    else:
        for rel in paths:
            lines.append(f"    - {rel}")
    return "\n".join(lines)


def cmd_check(full=False, *, repo_root=None, state_file=None):
    """Run the E4 read-only freshness diagnostic.

    Returns the AC5 exit code: 0 / 1 / 2.

    ``repo_root`` + ``state_file`` are injection seams for tests.
    """
    if repo_root is None:
        repo_root = _REPO_ROOT
    if state_file is None:
        state_file = _STATE_FILE

    # Import E1's checksum helper. Lazy so the CLI's other subcommands
    # don't pay the import cost when they don't need it.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import compose_freshness as _cf
    except Exception as e:  # noqa: BLE001
        print(
            f"check: could not import compose_freshness: {e}", file=sys.stderr
        )
        return 2

    stored, error = _load_state_checksum(state_file=state_file)
    if error:
        print(f"check: {error}", file=sys.stderr)
        return 2

    try:
        current = _cf.compute_compose_checksum(repo_root)
    except Exception as e:  # noqa: BLE001 — surface as exit 2
        print(f"check: could not compute checksum: {e}", file=sys.stderr)
        return 2

    # DS-10683 F1 fix: track drift as a flag instead of exiting early.
    # If --full is passed AND the checksum already mismatched, the
    # operator still wants the A4 dry-run output (which names the
    # specific composed files that need regeneration). Pre-fix, the
    # early ``return 1`` silently swallowed --full on drift.
    drift = False
    if stored is None:
        # AC8 covers clean / drifted / broken — first-boot isn't
        # called out, but the honest read is "no stored checksum to
        # compare against; the harness will run compose at next boot."
        # That's not drift; treat as clean from the diagnostic POV so
        # operators don't see a red signal on a fresh install.
        print("compose freshness: no stored checksum (first boot / fresh install)")
        print(f"  current checksum: {current}")
    elif stored != current:
        print(_format_drift_report(stored, current, repo_root), file=sys.stderr)
        drift = True
    else:
        print("compose freshness: clean")
        print(f"  checksum: {current}")

    # Post-E6 (#10685) Phase 3d.3: `--full` is deprecated. The downstream
    # `compose.py deploy-all --check` was retired (Option A) because the
    # v2 on-disk CLAUDE.md is LLM-polished and cannot byte-match a
    # deterministic in-memory compose. `--full` is accepted for backward
    # compat but emits a retirement notice and falls through to the
    # checksum-only exit semantics.
    if full:
        print(
            "WARNING: `squidsquad check --full` is deprecated. The "
            "underlying `compose.py deploy-all --check` was retired in "
            "#10685 Phase 3d.3 (v2 on-disk CLAUDE.md is LLM-polished, so "
            "byte-level drift-check is not a meaningful operation). "
            "Falling through to checksum-only freshness diagnostic.",
            file=sys.stderr,
        )
    return 1 if drift else 0


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print(USAGE)
        return 0

    cmd = args[0]

    if cmd == "start":
        role = args[1] if len(args) > 1 else None
        return cmd_start(role)
    elif cmd == "stop":
        role = args[1] if len(args) > 1 else None
        return cmd_stop(role)
    elif cmd == "restart":
        if len(args) < 2:
            print("Usage: squidsquad restart <role>", file=sys.stderr)
            return 2
        return cmd_restart(args[1])
    elif cmd == "status":
        return cmd_status()
    elif cmd == "shutdown":
        return cmd_shutdown()
    elif cmd == "check":
        full = "--full" in args[1:]
        extra = [a for a in args[1:] if a != "--full"]
        if extra:
            print(
                f"check: unrecognized arguments: {' '.join(extra)}",
                file=sys.stderr,
            )
            print("Usage: squidsquad check [--full]", file=sys.stderr)
            return 2
        return cmd_check(full=full)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(USAGE)
        return 2


if __name__ == "__main__":
    sys.exit(main())
