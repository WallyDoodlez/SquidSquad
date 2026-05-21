# CONTEXT-9688 — Orphan claude.exe subagents cleanup

**Issue**: #9688
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-20 (cycle 1537)
**Status**: open → ready-for-pickup (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9688 + this CONTEXT-9688.md combined are the contract for skill at pickup. The body describes the symptom; this file locks the fix mechanism + the architecture doc update.

---

## 1. Locked Decisions

All 8 RESEARCH-9688.md §5 questions answered (Q2 + Q6 collapsed into one after clarification). Decisions:

### D1. Live-subagent grace period (Q1)

**Locked: never kill a claude.exe whose parent process is alive**, regardless of age. Only orphans (dead parent) are eligible for cleanup.

Reasoning: Agent-tool subagents can legitimately run 12+ minutes (deepseek code review, long-running explorations). A live parent indicates the spawn is still being managed; we don't assume the agent abandoned it. Only when the parent dies do we conclude the subagent was orphaned.

### D2. Orphan identification + sweep strategy (Q2 + Q6 merged)

**Locked: sweep ALL orphan claude.exe processes globally, not per-clone.**

Reasoning: once a subagent's parent is dead, we can't reliably trace it back to a specific clone (cmd.exe with `--mcp-config <clone>/.squidsquad/mcp-agents.json` is gone with the parent). Attribution-by-clone is unreliable for dead-parent orphans. Cleanest model: orphans are global; whichever cycle fires the cleanup first sweeps them all.

Algorithm:
1. Build set of "protected PIDs" = for each role, read `.squidsquad/<role>/.claude-pid` → get cmd.exe PID → find the claude.exe whose `ParentProcessId == cmd.exe PID`. That claude.exe PID is protected.
2. For every other claude.exe in the process table whose CommandLine matches the npm-install path (`*\node_modules\@anthropic-ai\claude-code\bin\claude.exe`):
   - If `ParentProcessId` is alive → LIVE SUBAGENT, skip (per D1).
   - Else → ORPHAN, kill with `taskkill /F /PID <pid>`.

### D3. Missing or stale `.claude-pid` handling (Q3)

**Locked: skip cleanup for this run if ANY role's `.claude-pid` is missing or its referenced cmd.exe PID is dead.**

Reasoning: rather miss orphans than kill a real agent by mistake. A missing `.claude-pid` could mean the agent is mid-respawn — wait for next cleanup cycle when state has stabilized.

### D4. Logging (Q4)

**Locked: log every cleanup decision to `.squidsquad/diagnostics/orphan-cleanup.log`** (append-only, one JSON line per decision). Schema:

```json
{
  "timestamp": <epoch>,
  "pid": <claude_pid>,
  "parent_pid": <parent_pid>,
  "parent_alive": true|false,
  "decision": "kept"|"killed"|"skipped",
  "reason": "<human-readable>",
  "age_min": <float>
}
```

Do NOT comment on the tracker — too noisy.

### D5. Default enable (Q5)

**Locked: ON, no opt-out flag.** Cleanup runs every cycle and every reboot. No config flag.

Reasoning: human direction (cycle 1537) — orphan accumulation is a real problem and operators should never have to remember to enable cleanup.

### D6. Cross-platform behavior (Q7)

**Locked: cross-platform code, POSIX-safe.** On POSIX (Linux/macOS) the orphan scenario is much rarer because cmd.exe isn't in the chain — proper process-group propagation kills children when parent dies. The cleanup logic still runs, finds zero orphans, exits silently. Defensive; no harm.

Use existing `process_utils.is_process_alive` for the cross-platform liveness check.

### D7. Test approach (Q8)

**Locked: mock-based unit tests.** Synthetic process trees passed to the orphan-detection function; assert classification (protected / live-subagent / orphan). Skip end-to-end tests that spawn real subagents — fragile + slow + harder to clean up if test fails.

Test cases:
- Empty process list → no kills.
- Single protected agent (cmd.exe alive, claude.exe child) → no kills.
- 4 protected agents (full squad) → no kills.
- 1 protected + 1 orphan (claude.exe with dead parent) → 1 kill, parent PID logged.
- 1 protected + 1 live subagent (claude.exe with non-protected live parent) → no kills.
- Missing `.claude-pid` for one role → entire cleanup skipped (D3).
- Mix of all populations → only orphans killed.

### D8. Architecture doc update (NEW — folded in from human direction)

**Locked: update `docs/ARCHITECTURE.md` L2 Orchestration section** to document:
- Full process tree: `python.exe (thin_launcher) → cmd.exe (claude.CMD shim) → claude.exe (agent)`
- Why cmd.exe is in the chain (`.CMD` file requires `cmd.exe` to interpret on Windows; not a design choice)
- `.claude-pid` convention: stores the cmd.exe PID (the immediate parent of claude.exe), NOT the claude.exe PID itself
- Kill semantics:
  - **Reboot**: `taskkill /F /T /PID <cmd.exe PID from .claude-pid>` — `/T` kills the tree (cmd.exe + claude.exe both die)
  - **Orphan cleanup**: `taskkill /F /PID <orphan_claude.exe PID>` — orphan is leaf-level, no `/T` needed
- Three claude.exe populations (protected agent / live subagent / orphan) + the cleanup algorithm

This goes near the existing `thin_launcher.py` mention at line 58 of ARCHITECTURE.md, in the L2 Orchestration section.

---

## 2. Grounded File References

### 2.1 Primary fix sites

- `references/scripts/orphan_cleanup.py` (NEW) — the cleanup module with the detection + safe-kill logic per D2.
- `references/scripts/cycle_post.py` (~line 824 per RESEARCH-9588 §2.5 ordering) — invoke `orphan_cleanup.sweep()` near end-of-cycle.
- `references/scripts/boot_remote.py` — invoke `orphan_cleanup.sweep()` once at start of boot sequence, before respawning the target role.
- `docs/ARCHITECTURE.md` (L2 section, near line 58) — process-tree documentation per D8.

### 2.2 Shared helpers (existing)

- `references/scripts/process_utils.py:is_process_alive` — primitive for D2's parent-alive check.

### 2.3 New diagnostics output

- `.squidsquad/diagnostics/orphan-cleanup.log` — append-only JSONL per D4.

### 2.4 Tests

- `tests/test_orphan_cleanup.py` (NEW) — mock-based unit tests per D7.

---

## 3. Architecture Doc Insert (D8) — locked text

Insert this section near line 58 of `docs/ARCHITECTURE.md`, under L2 Orchestration:

```markdown
### Agent Process Tree

Each SquidSquad agent runs as a chain of three processes:

\`\`\`
python.exe (thin_launcher.py)
  └── cmd.exe (claude.CMD shim from npm install)
        └── claude.exe (the actual agent)
\`\`\`

Why cmd.exe is in the chain: `thin_launcher.py:149` resolves the claude binary via `shutil.which("claude")`, which returns `claude.CMD` on Windows (the npm shim). Running a `.CMD` file requires `cmd.exe` to interpret it, so Windows inserts `cmd.exe` between the launcher and the actual `claude.exe`. This is a Windows-only artifact of how `.CMD` shims work — POSIX systems launch `claude.exe` directly.

### `.claude-pid` convention

`.squidsquad/<role>/.claude-pid` stores the **cmd.exe** PID (the immediate parent of `claude.exe`), NOT the `claude.exe` PID itself. The name is historical — it was originally written assuming the launcher would spawn `claude.exe` directly. To find the actual agent `claude.exe` process: read `.claude-pid` → find the `claude.exe` whose `ParentProcessId` matches.

### Killing agents

- **Reboot (terminate agent + restart)**: `taskkill /F /T /PID <cmd.exe PID from .claude-pid>`. The `/T` flag kills the process tree — both `cmd.exe` and its `claude.exe` child terminate. The python `thin_launcher` (grandparent) sees its child exit and returns; the operator typically respawns via `boot_remote.py`.
- **Orphan cleanup**: `taskkill /F /PID <orphan claude.exe PID>`. Orphans are leaf processes with no children, so no `/T` needed. See #9688 for the cleanup mechanism.

### Three claude.exe populations

When examining live `claude.exe` processes, three categories matter:

1. **Protected agent** — `ParentProcessId` matches some role's `.claude-pid`. This is the live agent; never kill except via reboot.
2. **Live subagent** — `ParentProcessId` is alive but does NOT match any `.claude-pid`. Spawned by the agent's `Agent` tool (deepseek code review, exploratory research); legitimately in progress.
3. **Orphan** — `ParentProcessId` is dead. Subagent whose parent task completed but Windows didn't propagate the exit. Safe to terminate via the cleanup mechanism (#9688).
```

---

## 4. Acceptance (Restated)

- `orphan_cleanup.py` module exists with sweep + classify functions.
- `cycle_post.py` invokes `orphan_cleanup.sweep()` at end of cycle. Logs decisions.
- `boot_remote.py` invokes `orphan_cleanup.sweep()` before respawning a role.
- `.squidsquad/diagnostics/orphan-cleanup.log` accumulates JSONL lines as decisions are made.
- After a heavy multi-Agent-tool work session, the orphan claude.exe count for a clone stays ≤1 (the live agent itself).
- Cross-platform: on POSIX, cleanup runs and exits silently with zero kills.
- Unit tests in `tests/test_orphan_cleanup.py` cover the 7 D7 test cases.
- `docs/ARCHITECTURE.md` updated with the process-tree section per D8.

---

## 5. Sequencing

- Independent of #9588 (lazy-load) and #9725 (spawn prompt fix). Can ship in any order.
- Recommend after #9725 ships, since stable /loop firing makes cycle_post-based cleanup more reliable (orphans get swept every cycle vs occasionally).
- Upstream Claude Code bug report (Option E from RESEARCH §4) — track as a follow-up issue for skill to file. Not a blocker.

---

## 6. Risk Notes (for skill at pickup)

1. **Race during agent respawn**: while a role is mid-respawn, its `.claude-pid` might be stale (old PID before reboot completes). D3 mitigates: skip cleanup if any `.claude-pid` doesn't resolve to a live cmd.exe. Better to miss a sweep than kill the wrong process.
2. **Detection of cmd.exe → claude.exe child**: the algorithm walks from `.claude-pid` (cmd.exe) to find its claude.exe child. If a role's cmd.exe somehow has zero or multiple claude.exe children (shouldn't happen but edge case), log + skip that role.
3. **Cross-platform process-listing API**: Windows uses `Get-CimInstance Win32_Process` (powershell) or `wmic`/`tasklist`; POSIX uses `ps`. Need an abstraction. Recommendation: shell out to `tasklist /FO CSV /V` on Windows + `ps -eo pid,ppid,comm,args` on POSIX, parse output. Document the version/format assumptions.
4. **Performance**: process listing on Windows can be slow (~1-2s for `tasklist`). Cycle_post runs every cycle (30 min default). Acceptable. If cleanup takes >5s, log a warning.
5. **Idempotency**: multiple cleanup runs in quick succession (e.g., two agents finishing cycle_post simultaneously) should be safe — `taskkill` of an already-dead process is a no-op error, swallowed silently.

---

## 7. Out of Scope

- Upstream fix in Claude Code (track as separate follow-up).
- Killing the parent cmd.exe shim of a real agent (existing reboot flow handles this).
- Killing claude.exe processes outside SquidSquad's npm-install path — that's the user's own Claude Code IDE / other CLI sessions. The path-match check excludes them.
- Refactoring the launch chain to remove the cmd.exe shim layer (would require bypassing the .CMD shim — separate concern).

---

## 8. Open Questions Resolved (from RESEARCH-9688 §5)

| Q | Locked decision |
|---|----------------|
| Q1 | Never kill if parent alive |
| Q2 | Sweep all orphans globally (no per-clone attribution) — Q6 merged in |
| Q3 | Skip cleanup if `.claude-pid` missing or stale |
| Q4 | Log to `.squidsquad/diagnostics/orphan-cleanup.log` JSONL; no tracker comments |
| Q5 | **ON, no opt-out flag** (human direction cycle 1537) |
| Q6 | (merged into Q2) |
| Q7 | Cross-platform code; POSIX likely no-op |
| Q8 | Mock-based unit tests; 7 specific test cases enumerated in D7 |
| **D8** | Architecture doc update (NEW per human direction) |

---

## 9. Next Step

PM presents this CONTEXT-9688.md to the human for approval. On approval: PM comments "ready for pickup" on #9688. Skill picks up (autonomously since it's role:skill + status:open + bug type per `feedback_auto_approve_bugs`). Implementation should be ~200 LOC + tests + a short ARCHITECTURE.md insert.
