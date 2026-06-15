---
name: learning-claude-code-http-hooks-block-only-command-hooks-async
description: Claude Code native type:http hooks are SYNCHRONOUS (they block the tool call until the POST returns/times out; default http timeout is 600s) and CANNOT be made fire-and-forget — async/asyncRewake are supported only on type:command hooks. So a hook that fires on every tool call (PostToolUse/PostToolUseFailure) and must never block the agent has to be a type:command async:true hook, not http; use the exec form (command:python + args with ${CLAUDE_PROJECT_DIR}, which Claude Code substitutes itself cross-platform) and read role/payload from the inherited env + stdin
metadata:
  type: learning
type: learning
tags: [learning, claude-code, hooks, harness, liveness, telemetry, 12443, 12418, 12271, self-hosting]
created: 2026-06-15
updated: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker, learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter]
---

# Claude Code http hooks block; only command hooks can be async/fire-and-forget

**Built (#12443, #12271 liveness slice b):** per-clone `PostToolUse` / `PostToolUseFailure` hooks that POST an activity heartbeat to the harness on every tool call. The natural choice — a native `type: http` hook, like the SessionEnd hook slice (a)/#12418 used — is WRONG here. Verifying the hook API first (the [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]] reflex) surfaced the constraint that the §16 "native http, no shell wrapper" design had assumed away:

1. **`type: http` hooks are SYNCHRONOUS.** Claude Code blocks the tool call / agent turn until the POST completes, times out, or errors. (Network errors and timeouts are themselves non-blocking — execution continues — but a *reachable, healthy* server holds the turn for the full round-trip.)
2. **The default http-hook timeout is 600 seconds** (10 min), not a small value. A hung server on a per-tool-call hook would be catastrophic; a short `timeout` is mandatory if you stay on http.
3. **`async` / `asyncRewake` are supported ONLY on `type: command` hooks** — there is no fire-and-forget mode for http. So a hook that fires on every tool call and must NOT add latency has to be a `type: command` hook with `async: true`: Claude Code spawns it, ignores its exit code/output, and moves on — true zero-latency.
4. **Connection-refused on localhost is effectively instant** (kernel RST), so "harness down" doesn't stall a sync http hook much; the real cost is the per-call round-trip when the harness is UP, plus the timeout ceiling if it hangs. Still, "synchronous" ≠ "backgrounded" — if the contract says backgrounded, http does not satisfy it.

**The right shape for a per-tool-call telemetry hook:**
- `type: command`, `async: true`, **exec form**: `"command": "python", "args": ["${CLAUDE_PROJECT_DIR}/references/scripts/<script>.py"]`. `${CLAUDE_PROJECT_DIR}` is substituted by Claude Code ITSELF (not the shell) before spawn, so it resolves cross-platform (Windows + POSIX) with no shell-quoting hazard. The exec form avoids shell tokenization entirely.
- Command-hook subprocesses **inherit the agent process's full environment**, so a custom launch var (e.g. `$SQUIDSQUAD_ROLE`) is readable via `os.environ`. The hook **payload is still delivered on stdin** even with `async: true`.
- `allowedEnvVars` (the per-clone header interpolation knob) is an **http-only** field — irrelevant to command hooks.
- The script must be **absolutely fail-open**: never raise, always `sys.exit(0)` — a telemetry hook must never surface a non-zero exit or stall the agent. (With `async: true` the exit/output are ignored anyway, but belt-and-braces.)

**Reserve `type: http` for LOW-frequency / teardown hooks** (e.g. SessionEnd, once per session) where a brief synchronous block is acceptable and the no-shell-wrapper simplicity is worth it.

**How to apply:**
- Before wiring ANY Claude Code hook, confirm: does it fire per-tool-call (hot path) or once (cold)? Hot path → async command hook. Cold → http is fine.
- "Native http, no shell wrapper" reads cleaner in an arch doc but is unimplementable for hot-path telemetry — when a doc's mechanism contradicts a hard latency requirement, surface the doc-drift (here: HARNESS-ARCH §16) rather than silently bending the requirement. Same class as the `/work/assign`-endpoint-that-doesn't-exist drift.
- A throttle belongs on the *recording* side, not the emit side: the harness updates in-memory state every heartbeat (cheap, what observers read) but rate-limits the state-FILE write — so per-tool-call frequency doesn't thrash disk.
