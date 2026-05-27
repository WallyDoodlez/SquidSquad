# Harness Spawn Architecture — Feasibility Investigation

_What was learned from investigating "can the harness spawn `claude` directly instead of via `wt → bash → thin_launcher → cmd → claude`?" — and what's actionable from it._

> **Status**: investigation complete, 2026-05-26. **Verdict: the big "harness owns claude directly" redesign is not viable on the current Anthropic billing model.** A real terminal is required to keep subscription billing; piping stdin/stdout to `claude` auto-demotes it to the Agent SDK billing pool. Today's `wt → bash → thin_launcher → cmd → claude` chain is *not* legacy cruft — `wt.exe` is load-bearing because it provides the TTY that keeps the session on subscription billing. The achievable simplifications are smaller: drop the `cmd.exe` npm shim and the `bash` layer. See §3 for the actionable smaller proposal. Sections §4–§7 record the investigation that led to the verdict.
>
> Companion to [`HARNESS-ARCH.md`](HARNESS-ARCH.md) (current state) and [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (cycle integration / v2 event-driven mode).

---

## 1. The verdict

A **TTY is required** to keep agent sessions on the interactive Claude subscription billing model. When `claude.exe`'s stdout is a pipe instead of a TTY, it auto-detects non-interactive mode and switches to the Agent SDK billing pool — separately metered ($20/$100/$200/mo SDK credit for Pro/Max-5x/Max-20x respectively from 2026-06-15, then API rates per-token). This is true even without the `-p` flag.

Concretely:

- The harness **cannot** own `claude.exe`'s stdin/stdout via plain pipes and still bill against the existing Max 20x subscription. Verified by §4.3.
- `wt.exe` (Windows Terminal) is the simplest way to provide a TTY today, and is what the existing chain already uses. The corollary doesn't follow that `wt.exe` is the *only* viable TTY provider — see the open ConPTY question below.

### 1.1 Open question — ConPTY as a middle ground

The pipe-vs-TTY test proved *"pipes cause API billing; a real terminal keeps subscription billing"*. It did NOT test *"a programmatic pseudoterminal (ConPTY on Windows, `pty.openpty` on POSIX) keeps subscription billing"*. The two are not the same thing.

A ConPTY-based middle ground would look like:

1. Harness allocates a ConPTY pair (master FD + slave FD).
2. Spawns `claude.exe -p --input-format stream-json --output-format stream-json` with the slave FD attached as its stdin/stdout. From claude's perspective, it has a TTY.
3. Harness reads/writes stream-json on the master FD — same protocol as the closed pipe-based proposal, but over a PTY.

If claude treats the PTY as a TTY for billing purposes (likely — the detection is almost certainly `isatty(stdout)`, which returns true for PTY slaves), then we'd get *both* subscription billing and programmatic harness control without screen-scraping. The first time this doc made the "PTY emulation is strictly more complex" claim it conflated PTY allocation with TUI scraping — those are distinct.

**Status:** untested. Listed in §7 follow-ups. The "TTY required" verdict stands either way; the question is *which* TTY provider, not *whether*. Until tested, `wt.exe` remains the operational answer and §3's smaller proposal stands.

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

This is essentially "what `_resolve_claude_exe_pid` already does, but at boot instead of runtime, and against the shim *script* instead of the process tree."

A working prototype lives at [`references/experiments/resolve_claude.py`](../references/experiments/resolve_claude.py) — **~190 lines** including comments, docstrings, and the chain-walker. Validated end-to-end on this Windows/npm install (§4.1.1) and against the Popen-tree comparison (§4.1.2). The prototype covers Windows `.cmd` / `.bat` / `.ps1` shims and POSIX bash shims; the POSIX paths are written but untested (no POSIX install on the test machine).

**Net:** §3.1 is real but more work than the one-line sketch implied. The savings still justify it — ~250 lines of `_resolve_claude_exe_pid` + descendant-walker out, ~190 lines of boot-time resolver in, the singleton race class gone. Net `~60 lines deleted + a much simpler invariant` (Popen.pid IS claude.exe, always).

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

### 4.1.1 Test: portable install resolver works on this machine ✅

Script: [`references/experiments/resolve_claude.py`](../references/experiments/resolve_claude.py)

Starts from `shutil.which("claude")`, parses the `.cmd` shim's quoted forward path, resolves the relative `node_modules\@anthropic-ai\claude-code\bin\claude.exe`, then Popens `--version` against the resolved path to confirm it runs. Output on this machine:

```
ENTRY: C:\Users\naaht\AppData\Roaming\npm\claude.CMD
HOP 1: C:\Users\naaht\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe
verify: --version OK -> '2.1.140 (Claude Code)'
```

**Coverage caveats** (post-DeepSeek audit):

- **Tested:** the multi-line npm `.cmd` shim format (`SET dp0=%~dp0` followed by `"%dp0%\…\.exe"`) — that's what this machine ships.
- **Code path written but untested:** the older one-line `%~dp0` npm `.cmd` format; `.bat` (shares the cmd regex); `.ps1`; POSIX bash shims. The synthetic-string unit tests in the file's regex match correctly against literal samples of each format, but no real install of those variants was available to verify end-to-end. The POSIX parser specifically targets the standard npm POSIX shim shape (`exec "$basedir/node" "$basedir/.../cli.js" "$@"`) — earlier review noted the prior regex was structurally incompatible with that shape; the fixed regex picks the LAST `$basedir`-rooted argument off the `exec` line.
- **Broken-chain handling:** if a shim points to a non-existent target on disk, the resolver raises `BrokenShimChain` rather than silently returning the shim itself. Earlier review caught that a silent fallback to the shim would re-introduce the cmd.exe wrapper PID problem this resolver exists to avoid.

### 4.1.2 Test: `Popen(claude.cmd)` vs `Popen(claude.exe)` process trees ✅

Script: [`references/experiments/spawn_tree_test.py`](../references/experiments/spawn_tree_test.py)

Spawns `--help` two ways (longer-running than `--version` to widen the toolhelp32 snapshot window — see audit note below) and snapshots the process tree immediately:

| | `Popen.pid` resolves to | Descendants captured | stdout captured |
|---|---|---|---|
| **Test B** (`claude.cmd` shim) | **cmd.exe** | `claude.exe` (depth 1) + `conhost.exe` (depth 2) | empty (cmd wrapper's stdout, not claude's) |
| **Test A** (resolved `claude.exe`) | **claude.exe** | `reg.exe` × 2 + `conhost.exe` × 2 (claude probes the registry at startup) | `'Usage: claude [options] [command] [prompt]...'` |

The short-lived `cmd.exe` in Test B is exactly what `_resolve_claude_exe_pid` was built to walk past. With Test A's direct spawn, there's nothing to walk — `Popen.pid` is already claude.exe. The descendant-walker becomes unnecessary code; the singleton race class (cmd-wrapper exits before next thin_launcher invocation → stale `.claude-pid`) becomes structurally impossible.

**Audit notes** (post-DeepSeek):

- **conhost descendant asymmetry is informative, not a bug.** The test uses `creationflags=DETACHED_PROCESS`, which suppresses console inheritance for the *direct* child. In Test A, claude.exe is the direct child, so no console — no conhost as its direct descendant. In Test B, `cmd.exe` is the direct child *and* it's a console host, so it spawns its own grandchild console for claude.exe (depth 2). That asymmetry directly mirrors why `thin_launcher` needed the descendant walker in the first place.
- **Cross-reference for the "deletable" claim:** `_resolve_claude_exe_pid` + `_win32_list_descendants` + `_posix_list_descendants` are called only from `references/scripts/thin_launcher.py` itself, with one dedicated test in `tests/test_thin_launcher_10101.py`. No other consumers in the codebase. The "~250 lines deletable" estimate holds (modulo updating that test file alongside).
- **Race window in the snapshot loop is bounded but not eliminated.** The test now uses `--help` instead of `--version` (longer output, longer-lived process) to give toolhelp32 a wider window. If the spawn is missed entirely on a fast machine, the `INCONCLUSIVE` branch now exits with code 3 (not 0) so CI does not mark inconclusive runs as success.

### 4.2 Test: `--input-format stream-json` supports multi-turn over stdin

Two `{"type":"user",...}` lines on stdin → two complete init/result event pairs in stdout, same `session_id`. Process exits on EOF, blocks on empty stdin (pipe semantics). Token cache fully reused across turns: turn-1 `cache_creation_input_tokens: 70,255`; turn-2 `cache_read_input_tokens: 70,255` + `cache_creation: 85`.

This confirmed that the architecture *would have worked technically* — Claude Code's official streaming I/O is the right shape for what was wanted. The blocker was §4.3, not the protocol.

### 4.3 Test: pipe-vs-TTY mode-switching ⚠️

The most consequential test in this investigation. Two variants, same observed behavior:

```sh
# Variant A: no -p, piped stdin/stdout
printf 'reply pong\n' | claude.exe --model haiku
# → "pong" + exit 0     (print-mode behavior, not interactive)

# Variant B: same path, stream-json output
printf 'reply pong\n' | claude.exe --output-format stream-json --verbose --model haiku
# → {"type":"result", ..., "total_cost_usd": 0.0157, ...}
```

What this directly proves:

- **Pipes auto-trigger non-interactive mode.** `claude --help` is explicit:
  > "The workspace trust dialog is skipped when Claude is run in non-interactive mode (via -p, **or when stdout is not a TTY**, e.g. piped or redirected output)."
- **Non-interactive turns carry `total_cost_usd` in the stream-json result envelope.** Verified above (Variant B).

**What this is an *inference* about — not a citation-backed proof:** that the presence of `total_cost_usd` definitively indicates the Agent SDK / API billing pool (rather than subscription billing). The chain of reasoning rests on:

1. `total_cost_usd` is a per-turn USD figure. Interactive subscription billing is flat-rate (no per-turn USD), so reporting per-turn USD only makes sense for metered API billing.
2. The Anthropic [Claude Help Center article on the Agent SDK](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) and the [June 2026 billing change reporting](https://the-decoder.com/claude-subscriptions-get-separate-budgets-for-programmatic-use-billed-at-full-api-prices/) describe `claude -p` as drawing from a separate Agent SDK credit pool / API rates — distinct from the interactive subscription.
3. Anthropic issues [#43333](https://github.com/anthropics/claude-code/issues/43333) and [#37686](https://github.com/anthropics/claude-code/issues/37686) document users observing `claude -p` billing against API charges, not subscription, while OAuth-authenticated to a Max plan.

None of those sources explicitly state *"the presence of `total_cost_usd` in stream-json output indicates non-subscription billing."* The verdict in §1 is a synthesis — strong enough that this proposal is closed, but readers should treat it as a load-bearing inference, not a quoted Anthropic guarantee.

**Reproducible script:** the test above can be re-run by anyone with this Claude Code install. It is intentionally NOT scripted into `references/experiments/` because each run incurs API cost (~$0.01–$0.10 at Haiku rates). Re-running is operator-discretion, not a hands-off CI check.

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

Four independent follow-ups, in increasing scope:

1. **The visual-confusion fix (smallest, near-trivial).** Make `wt.exe new-tab` close the tab when its child exits — invoke through a wrapper that waits-and-exits, or set `wt` to non-persistent mode. Removes the operator-confusion source that triggered this whole investigation. One-line change to `boot_remote._spawn_windows`.

2. **§3.2: drop `bash` layer (small).** `wt.exe` invokes `python thin_launcher.py` directly. One fewer process per agent, no functional change. Cross-platform: same change in `_spawn_macos` and `_spawn_linux` (which probably already use the script's shebang anyway).

3. **§3.1: drop `cmd.exe` shim (medium).** Requires productizing the portable install resolver. A working ~190-line prototype exists at [`references/experiments/resolve_claude.py`](../references/experiments/resolve_claude.py) and is validated by [`spawn_tree_test.py`](../references/experiments/spawn_tree_test.py) — see §4.1.1 / §4.1.2. Productizing means: move into `references/scripts/`, wire into `thin_launcher.py` boot path, cache the resolved path in `.squidsquad/config.md`, add real-install integration tests for the older `%~dp0` Windows shim, `.bat`/`.ps1` variants, and POSIX (the prototype handles these code paths but only the standard Windows shim was end-to-end-verified). Once landed: ~250 lines of descendant-walker out, ~190 lines of resolver in (net ~60 lines deleted), singleton race class gone. Verified that `_resolve_claude_exe_pid` + descendant walkers have no other callers in the codebase (only `thin_launcher.py` + its dedicated test file).

4. **§1.1: ConPTY spike (medium, conditional).** Test whether a programmatic ConPTY (Windows) or `pty.openpty` (POSIX) keeps subscription billing while still letting the harness drive `claude -p --input-format stream-json` over the PTY's master FD. This is the *one* path that could reopen the closed redesign — see §1.1. If billing stays interactive under PTY, the entire "harness owns claude" architecture becomes viable. If it doesn't, follow-up #3 remains the only achievable simplification. **Strictly experimental until the PTY billing question is answered.**

Defer the bigger direct-spawn redesign until follow-up #4 returns a result.

### 9.1 Audit history

This doc went through a DeepSeek code-review pass (output: `.squidsquad/skill/planning/REVIEW-HARNESS-DIRECT-SPAWN-DEEPSEEK.md`). 11 findings filed — F1/F2/F3 (resolver silent-failure bugs), F4 (DETACHED_PROCESS + conhost asymmetry — confirmed correct), F5/F6/F11 (test ergonomics), F7 (ConPTY untested — surfaced as follow-up #4), F8 (no other callers — verified), F9 (untested shim variants — caveated in §4.1.1), F10 (billing inference, not citation-backed proof — caveated in §4.3). All addressed in-thread; the resolver and test scripts were corrected before this section was added.
