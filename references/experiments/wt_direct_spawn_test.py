#!/usr/bin/env python3
"""wt -> claude direct spawn experiment.

Tests the §3.5 proposal: can `wt.exe new-tab` directly spawn `claude.exe`
(without thin_launcher / bash / cmd) while preserving:

  1. A real TTY for claude (subscription billing — already established)
  2. Environment variables passed from the harness (e.g. SQUIDSQUAD_ROLE)
  3. A locatable process tree we can monitor

This is a NON-API smoke test — uses `claude --version` so no tokens
spent. Cost: $0.

Run:
    python references/experiments/wt_direct_spawn_test.py

Side effect: opens one or two Windows Terminal tabs briefly (they
close when claude --version exits if your Windows Terminal settings
have closeOnExit set, otherwise they stick around). Operator can
close them.

Exits 0 on success regardless of finding; non-zero only on harness
infrastructure failure (wt not found, etc.). The findings are in
stdout — read them.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from resolve_claude import resolve_claude
    from spawn_tree_test import _snapshot_processes
except ImportError as e:
    print(f"FAIL: cannot import sibling experiments: {e}", file=sys.stderr)
    sys.exit(7)


SENTINEL_ENV_VAR = "WT_DIRECT_SPAWN_TEST_TOKEN"


def _find_wt() -> str | None:
    return shutil.which("wt")


def _list_claude_pids() -> set[int]:
    procs = _snapshot_processes()
    return {pid for pid, (_parent, name) in procs.items()
            if name.lower() == "claude.exe"}


def _parent_chain(procs: dict, pid: int, max_depth: int = 10) -> list[tuple[int, str]]:
    """Walk up the parent chain from `pid`. Returns list of (pid, exe_name)."""
    chain = []
    seen = set()
    cur = pid
    while cur and cur not in seen and len(chain) < max_depth:
        seen.add(cur)
        if cur not in procs:
            break
        parent, name = procs[cur]
        chain.append((cur, name))
        cur = parent
    return chain


# ----- Test 1: does the parent env propagate to wt-spawned children? -----

def test_env_propagation() -> dict:
    """Spawn `wt new-tab cmd /c "echo %WT_DIRECT_SPAWN_TEST_TOKEN% > out.txt"`
    with the env var set in the parent. After the tab runs, check the file.

    cmd.exe re-enters the picture for this test because we need it to
    echo an env var and write to a file — neither is something we'd ask
    claude.exe to do. The test isolates the env-propagation question.
    """
    print("\n=== Test 1: env propagation through wt new-tab ===")
    wt = _find_wt()
    if not wt:
        return {"name": "env_propagation", "ok": False, "reason": "wt not found on PATH"}

    out_file = Path.cwd() / ".squidsquad" / "skill" / "planning" / "wt-env-probe.txt"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    if out_file.exists():
        out_file.unlink()

    sentinel_value = f"PROPAGATED-{int(time.time())}"

    # Set env var in our subprocess's env
    env = os.environ.copy()
    env[SENTINEL_ENV_VAR] = sentinel_value

    wt_argv = [
        wt, "new-tab",
        "--title", "env-probe",
        "cmd.exe", "/c",
        f'echo %{SENTINEL_ENV_VAR}% > "{out_file}"',
    ]
    print(f"  spawning: wt new-tab cmd /c \"echo %{SENTINEL_ENV_VAR}% > <file>\"")
    print(f"  parent env {SENTINEL_ENV_VAR}={sentinel_value}")

    try:
        subprocess.run(wt_argv, env=env, timeout=20, check=False,
                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    except subprocess.TimeoutExpired:
        return {"name": "env_propagation", "ok": False, "reason": "wt new-tab timed out"}

    # The wt client exits immediately after telling the daemon to create
    # the tab. The cmd.exe in the tab runs asynchronously. Poll the file.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if out_file.exists() and out_file.read_text(encoding="utf-8", errors="replace").strip():
            break
        time.sleep(0.2)

    if not out_file.exists():
        return {"name": "env_propagation", "ok": False,
                "reason": "probe file never appeared (tab may not have run)"}

    captured = out_file.read_text(encoding="utf-8", errors="replace").strip()
    print(f"  tab wrote: {captured!r}")

    propagated = sentinel_value in captured
    print(f"  env var visible in tab: {propagated}")
    print(f"  ({'expected — wt would inherit parent env' if propagated else 'NOT propagated — daemon-spawned tabs run with daemon env, not client env'})")
    return {
        "name": "env_propagation",
        "ok": propagated,
        "captured": captured,
        "expected": sentinel_value,
    }


# ----- Test 2: direct spawn of claude.exe via wt new-tab -----

def test_direct_spawn() -> dict:
    """Spawn `wt new-tab <claude.exe> --version` and verify a claude.exe
    process appears with the expected parent (WindowsTerminal.exe or
    a conhost descendant), NOT a child of cmd.exe.
    """
    print("\n=== Test 2: wt new-tab <claude.exe> --version ===")
    wt = _find_wt()
    if not wt:
        return {"name": "direct_spawn", "ok": False, "reason": "wt not found"}

    claude_exe, _, _ = resolve_claude()
    print(f"  resolved claude.exe: {claude_exe}")

    # Pre-snapshot: existing claude.exe PIDs
    pre_pids = _list_claude_pids()
    print(f"  existing claude.exe PIDs (pre-spawn): {len(pre_pids)}")

    wt_argv = [
        wt, "new-tab",
        "--title", "direct-spawn-test",
        "-d", str(Path.cwd()),
        str(claude_exe), "--version",
    ]
    print(f"  spawning: wt new-tab ... {claude_exe.name} --version")

    try:
        subprocess.run(wt_argv, timeout=20, check=False,
                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    except subprocess.TimeoutExpired:
        return {"name": "direct_spawn", "ok": False, "reason": "wt timed out"}

    # Poll for a new claude.exe PID
    new_pid = None
    new_parent_chain = []
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        procs = _snapshot_processes()
        current_claudes = {pid for pid, (_p, name) in procs.items()
                           if name.lower() == "claude.exe"}
        delta = current_claudes - pre_pids
        if delta:
            new_pid = next(iter(delta))
            new_parent_chain = _parent_chain(procs, new_pid)
            break
        time.sleep(0.1)

    if new_pid is None:
        return {"name": "direct_spawn", "ok": False,
                "reason": "no new claude.exe process appeared in 8s"}

    print(f"  new claude.exe PID: {new_pid}")
    print(f"  parent chain (bottom-up):")
    for pid, name in new_parent_chain:
        print(f"    pid={pid}, exe={name}")

    # Verdict: claude.exe should NOT be a descendant of cmd.exe
    chain_names = [name.lower() for _pid, name in new_parent_chain]
    has_cmd_ancestor = "cmd.exe" in chain_names[1:]  # skip claude itself
    has_terminal_ancestor = any("terminal" in n.lower() or "openconsole" in n.lower() or "conhost" in n.lower()
                                 for n in chain_names[1:])

    print(f"  cmd.exe in ancestry: {has_cmd_ancestor}")
    print(f"  WindowsTerminal/conhost in ancestry: {has_terminal_ancestor}")

    return {
        "name": "direct_spawn",
        "ok": not has_cmd_ancestor,
        "new_pid": new_pid,
        "chain": [(p, n) for p, n in new_parent_chain],
        "has_cmd_ancestor": has_cmd_ancestor,
        "has_terminal_ancestor": has_terminal_ancestor,
    }


def main() -> int:
    print("3.5 feasibility experiment - wt -> claude direct spawn")
    print("=" * 60)

    t1 = test_env_propagation()
    t2 = test_direct_spawn()

    print("\n" + "=" * 60)
    print("=== Summary ===")
    for t in (t1, t2):
        status = "PASS" if t["ok"] else "FAIL"
        print(f"  [{status}] {t['name']}: {t.get('reason', '')}")

    print("\nVerdict for §3.5:")
    if t2["ok"] and t1["ok"]:
        print("  [GREEN] Direct spawn works AND env vars propagate.")
        print("  §3.5 is viable as proposed.")
        return 0
    elif t2["ok"] and not t1["ok"]:
        print("  [YELLOW] Direct spawn works but env vars do NOT propagate via wt new-tab.")
        print("  §3.5 viable with caveat: SQUIDSQUAD_ROLE needs an alternate channel")
        print("  (CLI arg to cycle scripts, current-state file, or written to .env file).")
        return 0
    elif not t2["ok"] and t1["ok"]:
        print("  [RED] Env propagation works but direct spawn failed to produce a clean tree.")
        return 0
    else:
        print("  [RED] Both tests failed — §3.5 needs major rethinking.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
