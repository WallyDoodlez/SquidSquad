# Harness Spawn Architecture — Feasibility Investigation

_What was learned from investigating "can the harness spawn `claude` directly instead of via `wt → bash → thin_launcher → cmd → claude`?" — and what's actionable from it._

> **Status**: investigation complete, 2026-05-26. **Verdict: the big "harness owns claude directly" redesign is not viable on the current Anthropic billing model.** A real terminal is required to keep subscription billing; piping stdin/stdout to `claude` auto-demotes it to the Agent SDK billing pool. Today's `wt → bash → thin_launcher → cmd → claude` chain is *not* legacy cruft — `wt.exe` is load-bearing because it provides the TTY that keeps the session on subscription billing. The achievable simplifications are smaller: drop the `cmd.exe` npm shim and the `bash` layer. See §3 for the actionable smaller proposal. Sections §4–§7 record the investigation that led to the verdict.
>
> Companion to [`HARNESS-ARCH.md`](HARNESS-ARCH.md) (current state) and [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (cycle integration / v2 event-driven mode).

---

## 1. The verdict

A real terminal is required to keep agent sessions on the interactive Claude subscription billing model. When `claude.exe`'s stdout is a pipe instead of a TTY, it auto-detects non-interactive mode and switches to the Agent SDK billing pool — separately metered ($20/$100/$200/mo SDK credit for Pro/Max-5x/Max-20x respectively from 2026-06-15, then API rates per-token). This is true even without the `-p` flag.

Concretely:
- The harness **cannot** own `claude.exe`'s stdin/stdout via plain pipes and still bill against the existing Max 20x subscription.
- The only way to harness-own `claude` while keeping subscription billing is full PTY emulation + driving the TUI programmatically. That is strictly *more* complex than today's chain, not less — defeats the purpose.
- `wt.exe` (Windows Terminal) is the cheapest TTY provider Windows has. It stays.

---

## 2. What this means for today's chain

The current per-agent process tree (Windows) is:

```
wt.exe (Windows Terminal tab, provides TTY)
 └ bash.exe
    └ python.exe (thin_launcher.py)
       └ cmd.exe (npm claude.CMD shim)
          └ claude.exe (the agent, sees TTY → subscription billing)
```

Every layer except `cmd.exe` (and arguably `bash.exe`) is doing real work. The investigation's mistake was assuming the chain was incidental complexity. It's not — most of it is in service of "give `claude.exe` a real terminal so subscription billing applies." That's load-bearing.

---

## 3. Actionable smaller proposal

What *can* be simplified without changing the billing model:

### 3.1 Drop the `cmd.exe` shim — Popen `claude.exe` directly

`claude.cmd` is a 7-line npm wrapper that resolves to and `EXEC`s `node_modules/@anthropic-ai/claude-code/bin/claude.exe`. Bypassing it means:

- `Popen([CLAUDE_EXE, ...])` returns claude.exe's PID directly. No descendant walk.
- Singleton enforcement becomes trivial: the PID file holds the actual `claude.exe` PID, alive == alive, dead == dead.
- The entire `_resolve_claude_exe_pid` + `_win32_list_descendants` + `_posix_list_descendants` machinery in `thin_launcher.py` (~250 lines) is deletable.
- The `#10101` ticket's failure mode (stale-wrapper PID after cmd exits) cannot recur because there's no wrapper to exit.

**Caveat — and this is the actual hard part:** path resolution. `shutil.which("claude")` returns the `cmd.exe` shim because that's what's on `PATH` (npm installs it that way deliberately). The real `claude.exe` lives several directories deep under `node_modules/@anthropic-ai/claude-code/bin/` and is *not* on `PATH`. So "just Popen the .exe directly" only works if we can reliably locate it across install variants:

| Install method | Where `claude.exe` (or equivalent) actually lives |
|---|---|
| npm global on Windows | `%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe` |
| npm global on macOS/Linux | `<npm-prefix>/lib/node_modules/@anthropic-ai/claude-code/cli.js` (no `.exe`; runs via node) |
| Anthropic native installer (Windows) | Under `%LOCALAPPDATA%\Programs\...` or similar, varies by version |
| Anthropic native installer (macOS) | `/Applications/Claude.app/Contents/MacOS/...` or `~/Applications/...` |

The shim-walking code (`_resolve_claude_exe_pid` + toolhelp32 ctypes block) exists *because* this path-resolution problem was hard enough that earlier direct-spawn attempts ran into it. The current architecture sidesteps it by letting `shutil.which("claude")` return the shim and then walking the process tree to find whatever the shim actually executed — that works for any install layout without needing to know it.

For §3.1 to land, we need an install-aware resolver. Sketch:

1. Start from `shutil.which("claude")` to get *some* entry point
2. If it ends in `.cmd`/`.bat`/`.ps1`, parse the script to find the `.exe` it forwards to (the npm shim's pattern is consistent: line 8 of `claude.cmd` literally contains the `.exe` path)
3. If it's a node CLI shim, resolve to the node binary + `cli.js` path
4. If it ends in `.exe` already (non-shim path), use it directly
5. Cache the resolved path in `.squidsquad/config.md` or similar so we only do it once per install

This is essentially "what `_resolve_claude_exe_pid` already does, but at boot instead of runtime, and against the shim *script* instead of the process tree." It's a different problem with a similar shape — maybe 80–150 lines, far less than the 250 lines deleted, but not free.

**Net:** §3.1 is real but more work than the original sketch implied. The savings (descendant walker + race class gone) still justify it, but the build is "write a portable install resolver," not "one-line change to use absolute path."

### 3.2 Drop the `bash` layer — `wt.exe` invokes Python directly

`boot_remote._spawn_windows` today shells out roughly as:

```python
[wt, "new-tab", "--title", f"squidsquad-{role}", "-d", str(clone_root),
 "bash", str(thin_launcher_path)]
```

The `bash` invocation exists because `thin_launcher.py` has a bash-style shebang and originally was a shell script. Just replace `bash <path>` with `python <path>` (or `pythonw.exe` if we don't want the python console to show). One fewer process per agent, no functional change.

### 3.3 Net per-agent tree under both changes

```
wt.exe (TTY, unchanged)
 └ python.exe (thin_launcher.py, unchanged role)
    └ claude.exe (no cmd shim)
```

Three processes instead of five. Singleton check is direct (`Popen.pid` == claude PID). No descendant walker. Process count for the v2 event-driven path still adds a sibling `event_poll.py`, but the main tree is leaner.

### 3.4 What does NOT change

- `wt.exe` stays — load-bearing for TTY/subscription billing.
- `thin_launcher.py` stays — singleton lock, `--append-system-prompt`, restart-on-exit-42, atomic `.claude-pid` write. Slimmed by ~250 lines (drop the descendant walker) but conceptually unchanged.
- The harness's HTTP API, EventLifecycleManager, EAD, intent state machine — all unchanged.
- The duplicate-spawn race that triggered this investigation in the first place is *not* fixed by these changes alone. That's a separate concern — see §5.

---

## 4. Feasibility evidence (what was actually tested)

Conducted 2026-05-26.

### 4.1 Test: direct spawn bypasses the npm shim ✅

```sh
"C:/Users/naaht/AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe" -p \
   --output-format stream-json --verbose --model haiku <<< 'Reply pong'
```

Direct invocation works. `Popen.pid` is the real claude.exe — no `cmd.exe` in the tree. Validates §3.1.

### 4.2 Test: `--input-format stream-json` supports multi-turn over stdin

Two `{"type":"user",...}` lines on stdin → two complete init/result event pairs in stdout, same `session_id`. Process exits on EOF, blocks on empty stdin (pipe semantics). Token cache fully reused across turns: turn-1 `cache_creation_input_tokens: 70,255`; turn-2 `cache_read_input_tokens: 70,255` + `cache_creation: 85`.

This confirmed that the architecture *would have worked technically* — Claude Code's official streaming I/O is the right shape for what was wanted. The blocker was §4.3, not the protocol.

### 4.3 Test: pipe-vs-TTY determines billing mode ⚠️

The critical test. Two variants, same conclusion:

```sh
# Variant A: no -p, piped stdin/stdout
printf 'reply pong\n' | claude.exe --model haiku
# → "pong" + exit 0     (print-mode behavior, not interactive)

# Variant B: same path, stream-json output
printf 'reply pong\n' | claude.exe --output-format stream-json --verbose --model haiku
# → {"type":"result", ..., "total_cost_usd": 0.0157, ...}
```

`total_cost_usd` in the result envelope is the smoking gun: subscription-billed interactive turns don't carry per-turn USD; only API-billed turns do. From `claude --help`:

> "The workspace trust dialog is skipped when Claude is run in non-interactive mode (via -p, **or when stdout is not a TTY**, e.g. piped or redirected output)."

Claude actively detects no-TTY and self-demotes. There is no flag that disables this detection without also disabling subscription billing.

---

## 5. Investigation: the duplicate-spawn race

The investigation was triggered by an observation that two `SQUIDSQUAD_ROLE=skill` Claude sessions appeared to be running concurrently. Root cause: the harness's auto-reboot loop spawned a fresh skill agent ~30 seconds after the prior skill session exited following its last cycle. From the operator's POV, the lingering `wt.exe` tab (which doesn't auto-close when its child claude.exe exits) made it look like both were live concurrently. In reality only one claude.exe was running at any time; the duplicate was visual, not actual.

This is *not* a bug. It's the harness's intended behavior. The proposal's framing of "delete the duplicate-spawn race" turned out to overstate the problem — the race class that *can* still occur (two concurrent `thin_launcher` invocations before either writes a `.claude-pid`) is mostly defused by `thin_launcher`'s singleton check at boot. Closing the visual-confusion gap is a separate small task — making `wt.exe new-tab` close the tab when its child exits, via a wrapper script.

---

## 6. Investigation: billing model

The big proposal would have used `claude -p`, putting all four agents on the Agent SDK billing pool. Researched billing (sources §8):

- **Today (pre-2026-06-15):** per Anthropic issues #37686 and #43333, `claude -p` with OAuth/Max auth silently billed as per-token API charges. One reporter hit $1,800 in 2 days of automation. Acknowledged bug.
- **2026-06-15 onward:** Anthropic formalizes the split. `claude -p` and Agent SDK draw from a new monthly SDK credit ($20 Pro / $100 Max 5x / $200 Max 20x), then fall through to API rates. SDK usage no longer counts toward the interactive subscription's limits.

Cost projection for the four-agent SquidSquad fleet on Sonnet 4.6 was **$150–$450/month above the existing $200/mo Max 20x plan**, depending on cycle rate and model mix. Mitigations considered:

| Mitigation | Verdict |
|---|---|
| Hybrid spawn (keep interactive billing, harness owns pipes) | **Closed by §4.3** — pipes always trigger print-mode billing |
| Cost cap via `total_cost_usd` circuit breaker | Possible, but degrades to "agents halt when credit runs out" — operationally fragile |
| Cheaper-model routing (Haiku for routine cycles) | Possible — Haiku 4.5 is ~10× cheaper than Sonnet. Stacks with cost cap. Still > $0 above subscription. |
| Defer / keep today's architecture | **Recommended.** Cost is flat at the Max 20x subscription. |

---

## 7. Out of scope (what didn't get tested)

These were on the list before the §4.3 verdict closed the broader investigation. Listed for completeness; not needed unless a future Anthropic billing change reopens the design space.

- 24-hour soak of `claude -p` with stream-json multi-turn input under sustained load
- Context-pressure exit behavior in stream-json mode
- Tool-call timeout / wedge semantics under harness ownership
- Stdin-write-while-prior-turn-mid-flight (would need supervisor-side serialization)
- PTY emulation + TUI screen-scraping (rejected for complexity)

---

## 8. Sources

- [Use the Claude Agent SDK with your Claude plan — Anthropic Support](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
- [Claude subscriptions get separate budgets for programmatic use — the-decoder.com](https://the-decoder.com/claude-subscriptions-get-separate-budgets-for-programmatic-use-billed-at-full-api-prices/)
- [Issue #43333: `claude -p` with OAuth bills as API usage, not Max subscription](https://github.com/anthropics/claude-code/issues/43333)
- [Issue #37686: `claude -p` caused $1,800 in two days of unintended API billing](https://github.com/anthropics/claude-code/issues/37686)
- [Claude Code Billing Change June 15, 2026 — buildthisnow.com](https://www.buildthisnow.com/blog/guide/mechanics/claude-billing-change-june-2026)

---

## 9. Recommended next step

Three independent follow-ups, in increasing scope:

1. **The visual-confusion fix (smallest, near-trivial).** Make `wt.exe new-tab` close the tab when its child exits — invoke through a wrapper that waits-and-exits, or set `wt` to non-persistent mode. Removes the operator-confusion source that triggered this whole investigation. One-line change to `boot_remote._spawn_windows`.

2. **§3.2: drop `bash` layer (small).** `wt.exe` invokes `python thin_launcher.py` directly. One fewer process per agent, no functional change. Cross-platform: same change in `_spawn_macos` and `_spawn_linux` (which probably already use the script's shebang anyway).

3. **§3.1: drop `cmd.exe` shim (medium).** Requires building the portable install resolver described in §3.1's caveat — parse the shim script or read npm metadata to locate the real `claude.exe`/`cli.js`, cache the result. Once done: ~250 lines of descendant-walker + the singleton race class go away. Worth doing but not free.

Defer the bigger direct-spawn redesign indefinitely; revisit if Anthropic's billing model changes.
