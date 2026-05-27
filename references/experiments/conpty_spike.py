#!/usr/bin/env python3
"""ConPTY spike — historical research script.

Tested whether a programmatic Windows pseudo-terminal (ConPTY, via
`pywinpty`) would change `claude.exe`'s billing pool when invoked with
`-p`. The hypothesis was that since pipes auto-demote claude to the
Agent SDK billing pool, a real TTY (PTY) might keep it on subscription
billing while still allowing the harness to drive I/O programmatically.

Result: ConPTY does NOT change the billing signal. `total_cost_usd`
appeared in the result envelope identically to pipe-mode runs, indicating
the `-p` flag is the dominant trigger for non-interactive billing
regardless of TTY-presence. Plus, `--input-format stream-json` was found
non-functional over a PTY (claude errors with "Input must be provided
either through stdin or as a prompt argument").

Kept in the repo as historical evidence — the §14 proposed simplification
in docs/HARNESS-ARCH.md takes a different path (keep wt.exe for the TTY,
delete the middle layers, no PTY needed).

The test cannot directly confirm which billing pool was charged — that
requires checking the Anthropic dashboard out-of-band. What it CAN
observe:

  1. Does claude run under PTY at all? (isalive after spawn)
  2. Does `--input-format stream-json` work over a PTY? (does the user
     message get processed; does a result envelope come back)
  3. Does the result envelope still carry `total_cost_usd`?
     - presence → strong signal of metered-API billing (same as pipe mode)
     - absence → suggestive that billing path differs
  4. Are there other fields in the init / result envelope that
     differ between pipe-mode and PTY-mode? (apiKeySource, service_tier,
     anything billing-adjacent)

Operator confirms the actual billing pool by checking
https://console.anthropic.com / dashboard after this runs. The cost
should be < $0.10 on Haiku.

Run:
    python references/experiments/conpty_spike.py

Exits 0 on a clean run (regardless of verdict). Non-zero only on
infrastructure failure (PTY can't spawn, claude can't be found, etc.).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Import the resolver
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from resolve_claude import resolve_claude
except ImportError as e:
    print(f"FAIL: cannot import resolve_claude: {e}", file=sys.stderr)
    sys.exit(7)

try:
    from winpty import PtyProcess
except ImportError:
    print("FAIL: pywinpty not installed. `pip install pywinpty`", file=sys.stderr)
    sys.exit(7)


def _drain(proc: PtyProcess, max_wait_s: float = 30.0, idle_quit_s: float = 2.0) -> str:
    """Read from the PTY until claude exits or stdout goes idle.

    `claude -p` with stream-json input mode reads one user message, processes
    it, emits the result envelope, then... usually exits cleanly when stdin
    EOF is sent. We close stdin via sendeof() after writing our message and
    then drain.

    `idle_quit_s` is the per-read timeout; if nothing arrives for that long
    we assume claude is done. `max_wait_s` is the absolute ceiling.
    """
    deadline = time.monotonic() + max_wait_s
    buf = []
    last_data = time.monotonic()
    while time.monotonic() < deadline:
        if not proc.isalive():
            # Final drain after exit
            try:
                while True:
                    chunk = proc.read(4096)
                    if not chunk:
                        break
                    buf.append(chunk)
            except Exception:
                pass
            break
        try:
            chunk = proc.read(4096)
            if chunk:
                buf.append(chunk)
                last_data = time.monotonic()
            else:
                if time.monotonic() - last_data > idle_quit_s:
                    break
                time.sleep(0.05)
        except EOFError:
            break
        except Exception:
            # PTY may raise on closed handle; treat as end-of-stream
            break
    return "".join(buf)


def _extract_json_events(text: str) -> list[dict]:
    """Parse newline-delimited JSON events from the PTY output."""
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # ConPTY may inject \r before \n and ANSI sequences. The stream-json
        # output mode should still produce clean JSON per line.
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # Some lines may be stderr / log noise; skip
            continue
    return events


def main() -> int:
    # Locate the real claude.exe (no cmd shim) so we don't muddy the test
    # by re-introducing the wrapper layer the previous experiments fixed.
    try:
        claude_exe, _, _ = resolve_claude()
    except FileNotFoundError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"claude.exe path: {claude_exe}")

    # Pass the prompt positionally rather than via stream-json stdin.
    # First spike-run found that under a PTY, claude with --print and
    # stream-json input bailed out with "Input must be provided either
    # through stdin or as a prompt argument" — claude's stdin readiness
    # detection apparently doesn't wait on PTY-buffered input the same
    # way it does on subprocess.PIPE. Using a positional prompt sidesteps
    # the stdin-buffering question and isolates the billing-mode signal.
    prompt = "Reply with exactly the word PTY-SPIKE-OK and nothing else."

    # Spawn claude.exe with stream-json output under a real ConPTY.
    argv = [
        str(claude_exe),
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--model", "haiku",
        "--dangerously-skip-permissions",
    ]
    print(f"\nSpawning under ConPTY:")
    print(f"  argv: {argv}")
    print(f"  (cost-bounded: Haiku, single turn, < $0.10)\n")

    try:
        proc = PtyProcess.spawn(argv, cwd=str(Path.cwd()))
    except Exception as e:
        print(f"FAIL: PTY spawn raised {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(f"PTY spawned, pid={proc.pid}, isalive={proc.isalive()}, isatty={proc.isatty()}")

    # No stdin write — prompt is passed positionally. Drain output.
    output = _drain(proc, max_wait_s=120.0, idle_quit_s=8.0)

    if proc.isalive():
        print("(claude still alive after drain; sending EOF)")
        try:
            proc.sendeof()
        except Exception:
            pass
        more = _drain(proc, max_wait_s=10.0, idle_quit_s=2.0)
        output += more
        if proc.isalive():
            proc.terminate(force=True)

    # Dump raw output to a file for inspection
    dump_path = Path(".squidsquad/skill/planning/conpty-spike-raw-output.txt")
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(output, encoding="utf-8")
    print(f"\nPTY output ({len(output)} chars) written to {dump_path}")

    # Strip ANSI escape sequences for JSON parsing
    import re
    ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*[\x07\x1b]|\x1b[()][\x00-\x7f]')
    cleaned = ANSI_RE.sub('', output)
    print(f"After ANSI strip: {len(cleaned)} chars")

    events = _extract_json_events(cleaned)
    print(f"\nParsed JSON events: {len(events)}")
    for i, ev in enumerate(events):
        kind = ev.get("type", "?")
        subtype = ev.get("subtype", "")
        marker = f"{kind}/{subtype}" if subtype else kind
        print(f"  [{i}] {marker}")

    # The critical observation: did a result envelope come back, and does
    # it carry total_cost_usd?
    result_events = [ev for ev in events if ev.get("type") == "result"]
    init_events = [ev for ev in events if ev.get("type") == "system" and ev.get("subtype") == "init"]

    print("\n=== Verdict ===")
    if init_events:
        init = init_events[0]
        print(f"init.apiKeySource: {init.get('apiKeySource')!r}")
        print(f"init.model: {init.get('model')!r}")
    else:
        print("(no init event captured — claude may have errored before init)")

    if result_events:
        result = result_events[0]
        cost = result.get("total_cost_usd")
        is_error = result.get("is_error")
        text_result = result.get("result", "")
        service_tier = result.get("usage", {}).get("service_tier")
        print(f"result.is_error: {is_error}")
        print(f"result.result: {text_result!r}")
        print(f"result.total_cost_usd: {cost!r}")
        print(f"result.usage.service_tier: {service_tier!r}")

        if cost is None:
            print("\n[INTERESTING] total_cost_usd is NOT reported under ConPTY.")
            print("  This DIFFERS from the pipe-mode test (§4.3) where it WAS reported.")
            print("  Could indicate billing path differs. Confirm against the Anthropic")
            print("  dashboard before drawing conclusions.")
        elif cost == 0 or cost == 0.0:
            print("\n[INTERESTING] total_cost_usd is 0 under ConPTY.")
            print("  Could indicate the turn was charged against a non-USD pool (e.g.")
            print("  subscription limits). Worth confirming against dashboard.")
        else:
            print(f"\n[CLOSED] total_cost_usd = ${cost:.4f} reported under ConPTY.")
            print("  Same shape as pipe-mode (§4.3). PTY does NOT change the billing")
            print("  signal. The `-p` flag is the dominant trigger; TTY presence")
            print("  does not override it. Follow-up #4 closes.")
    else:
        print("(no result event captured — test inconclusive)")

    print("\n--- Operator follow-up ---")
    print("Check https://console.anthropic.com / your Anthropic billing dashboard.")
    print("If this turn shows up as an Agent SDK / API charge: ConPTY didn't help.")
    print("If it shows on the subscription dashboard with no per-token charge: reopened.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
