# RESEARCH-9688 — Orphan claude.exe subagents accumulate on Windows

**Issue**: #9688
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-20 (cycle 1537)

---

## 1. Question

During heavy multi-Agent-tool work sessions on Windows, child `claude.exe` subagent processes survive past their parent task completion, accumulating as orphans. By the end of a long session, a single agent clone may have 8+ orphan claude.exe processes (~2300 CPU sec + 500MB+ RAM cumulative). What's the right cleanup mechanism + where does it live?

---

## 2. Live Observation (Cycle 1535 Forensic)

### 2.1 Symptom (already documented in #9688 body)

- `D:\Dev\Dev\SquidSquad-2` (skill clone) accumulated 8 claude.exe processes during heavy #9398 + #9574 + #9588 work.
- Only 1 was the real skill agent.
- 7 were orphan subagents from Agent-tool calls (deepseek code reviews, exploratory research, etc.).
- All had dead parent processes (cmd.exe that exited).
- Cleanup required manual `taskkill /F /PID` on each.

### 2.2 Process tree of a healthy agent

For each role, the live tree is:
```
python.exe (thin_launcher)
  └── cmd.exe (claude.CMD wrapper)
        └── claude.exe (the actual agent)
```

Per the current process snapshot:
```
PM:    python 608300  → cmd 1012600 → claude 1434880
Skill: python 329560  → cmd 1111788 → claude 1547712
QA:    python 300068  → cmd 1330520 → claude 1543244
DM:    python 833908  → cmd 650888  → claude 1676936
```

`.claude-pid` files contain the **cmd.exe PID** (e.g., `cat skill/.claude-pid` → `1111788`), NOT the claude.exe PID. This matters for identification logic.

### 2.3 Subagent process tree

When the agent uses the Agent tool, Claude Code internally spawns a child claude.exe. From the orphan PIDs observed during the cycle-1535 incident:

```
parent cmd.exe (e.g. 962832, 1183004, 145872, etc.) — short-lived
  └── claude.exe (subagent — survives parent exit)
```

The parents are short-lived because they're "task-scoped" — created when the Agent tool fires, exited when the task completes. The child claude.exe doesn't exit because Windows lacks process-group propagation; the parent's exit doesn't signal the child.

---

## 3. The Identification Problem

The cleanup needs to distinguish three populations of claude.exe:

| Population | How to identify | Action |
|------------|----------------|--------|
| **Real agent** | claude.exe whose `ParentProcessId` matches the cmd.exe whose PID is in `.claude-pid` for some role | Never kill |
| **Live subagent** | claude.exe whose parent is alive AND parent path/command matches an Agent-tool spawn pattern | Wait (or short grace period) — may still be doing work |
| **Orphan subagent** | claude.exe whose parent is dead AND path matches a SquidSquad clone | Safe to kill |

### 3.1 Distinguishing "real agent" from "subagent" reliably

Algorithm:
1. For each role, read `.squidsquad/<role>/.claude-pid` → get `<launcher_pid>` (this is the cmd.exe PID, despite the name).
2. Find the claude.exe whose `ParentProcessId == <launcher_pid>`.
3. That claude.exe is the real agent. Track its PID. **NEVER kill.**
4. All other claude.exe processes matching the clone path are subagents (live or orphan).

### 3.2 Path-matching is critical

The clone path identifies which role owns a process. Examples:
- `C:\Users\naaht\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe` — invoked WITH `cwd` in agent clone → its env (per `Get-CimInstance` `CommandLine` field) doesn't directly show clone path, BUT we can correlate via the parent chain.
- The cleaner signal: the launching process tree's `cwd` (working directory) at the time of spawn.

Actually simpler: in PowerShell `Get-CimInstance Win32_Process`, the `CommandLine` of the cmd.exe shim contains the MCP config path: `--mcp-config D:\Dev\Dev\SquidSquad-2\.squidsquad\mcp-agents.json`. That contains the clone path. So:

- Walk parent chain of any claude.exe up to a cmd.exe; check cmd.exe `CommandLine` for the clone-path substring; assign claude.exe to that role.

But subagent spawns don't go through cmd.exe — they're direct claude.exe → claude.exe spawns with `--type=...` argument visible per R4. So the simpler check is on subagent claude.exe's own CommandLine:
- Real agent: no `--type=` flag (or `--type=client`).
- Subagent: has `--type=renderer` / `--type=utility` / `--type=gpu-process` / etc. — these are Electron-internal subprocesses, NOT Agent-tool subagents.

Actually this is the Claude Code DESKTOP APP (the IDE), not our CLI agents. Our CLI agents don't have these renderer/utility subprocesses. The orphans I observed during cycle-1535 had **no `--type=` flag** — they looked like real CLI claude.exe instances spawned via Agent tool.

### 3.3 Empirical signature of an Agent-tool subagent on Windows

From the cycle-1535 orphans, their command lines all started with `"C:\Users\naaht\AppData\Roaming\npm\\node_modules\@anthropic-ai\claude-code\bin\claude.exe"` — same as the parent agent. The differentiator was the PARENT — orphan parents were short-lived processes (PIDs like 962832, 1183004 that existed briefly then died), NOT the long-lived cmd.exe wrapper of the real agent.

So the algorithm is:
1. For each claude.exe in the process list:
   - If `ParentProcessId == <launcher_cmd_pid>` for any role's `.claude-pid` → REAL AGENT, skip.
   - Else if `is_process_alive(ParentProcessId)` → LIVE SUBAGENT, skip (may still be working).
   - Else (parent is dead) → ORPHAN, kill.

This gives us a safe + simple cleanup rule.

---

## 4. Options Surveyed

### Option A — Periodic cleanup in cycle_post.py

Add an orphan-detection step at end of `cycle_post.py` that runs every cycle. Detects + kills orphan claude.exe with safety checks.

**Pros**: runs frequently (per cycle), orphans don't accumulate; mechanical; no new processes; uses existing scheduling.
**Cons**: per-cycle CPU cost (small, but added to every cycle); only runs when an agent is itself cycling — if all agents stall, orphans persist; risks killing a still-running subagent if grace period is too short.

### Option B — Standalone cleanup script run on schedule

New `references/scripts/orphan_cleanup.py` invoked via cron / scheduled task / harness. Runs independently of agent cycles.

**Pros**: works even when agents are stalled (the original observation that triggered this issue); doesn't slow agent cycle; tunable cadence.
**Cons**: adds another scheduled job to set up; orchestration question (cron is OS-specific; harness scheduling adds harness dependency); requires careful coordination with agent cycles.

### Option C — Per-spawn cleanup in boot_remote.py

When boot_remote spawns a new agent, sweep orphans of THAT role's clone before respawn.

**Pros**: cleans up exactly when boot happens (the natural cleanup time); already integrated with boot_remote which is the agent-lifecycle entry point.
**Cons**: only fires on respawn; orphans accumulate between respawns (the actual problem we saw).

### Option D — Hybrid: cleanup at both cycle_post AND on respawn

Option A + Option C. Per-cycle low-cost cleanup + thorough sweep on respawn.

**Pros**: defense in depth; covers both "agent is cycling" and "agent is dead, operator reboots" cases.
**Cons**: two implementation surfaces; needs to be DRY (shared helper module).

### Option E — Upstream fix in Claude Code

File the orphan-on-Agent-tool-completion bug with the Claude Code team. They control the spawn lifecycle and could fix it at the source.

**Pros**: root cause fix; benefits the broader Claude Code user base on Windows.
**Cons**: external timeline; can't ship our fix today; status of upstream awareness unknown.

### Recommendation

**Option D (Hybrid)** for robust handling. Concretely:
- New `references/scripts/orphan_cleanup.py` module with the detection + safe-kill logic.
- Called from `cycle_post.py` near end-of-cycle (per-cycle low-cost path).
- Called from `boot_remote.py` before respawn (thorough sweep path).
- Single source of truth for the logic (DRY).

This is more surface area than Option A alone, but the cycle-1535 incident showed the failure mode where ALL agents stall and orphans accumulate while no cycles fire. Option A wouldn't have helped that case.

Plus: **also file the upstream bug with Claude Code** (Option E) as a separate non-blocking item. Could be filed by skill or PM during/after #9688 ships. Track as a follow-up.

---

## 5. Open Questions for CONTEXT (Phase 2)

1. **Grace period for live subagents**: if a subagent's parent process IS alive, how long do we wait before considering it abandoned? Subagent tasks can take 12+ minutes (deepseek code review). Recommendation: never kill a claude.exe whose parent IS alive, regardless of age. Only orphans (dead parent) are eligible.

2. **Clone-path matching strategy**: do we identify candidate orphans by walking the parent chain to find a cmd.exe with the agent's mcp-config path, OR by some other signal? Recommendation: the parent-PID check vs `.claude-pid` is the primary signal; clone-path matching is a sanity check.

3. **What if `.claude-pid` is missing or stale?** Could happen during agent transitions. Recommendation: if no `.claude-pid` for any role, skip cleanup for this run (better to miss orphans than kill the real agent by mistake).

4. **Logging**: should each kill be logged to diagnostics + tracker? Recommendation: log to `.squidsquad/diagnostics/orphan-cleanup.log` with PID, age, parent PID, decision. Don't comment on tracker (too noisy).

5. **Configurable enable flag**: should this be on by default or opt-in via config.md? Recommendation: on by default. Opt-out flag `cleanup-orphans: no` for operators who want to debug or use external tooling.

6. **Per-role isolation**: when PM's cycle_post runs the cleanup, should it touch ONLY PM-clone orphans, or sweep all clones? Recommendation: only PM-clone orphans. Each agent sweeps its own clone. Cross-clone sweeping risks accidentally killing another role's live subagent.

7. **Linux/macOS**: does the orphan problem exist there too? Unix has proper process-group propagation, so killing the parent cmd shell should kill children. Recommendation: write the cleanup as cross-platform; on POSIX it'll likely be a no-op because parents propagate to children correctly. Defensive code, no harm.

8. **Test approach**: how to unit-test the orphan detection? Recommendation: mock out `Get-CimInstance` / process listing; provide synthetic process trees; assert the algorithm correctly classifies real-agent / live-subagent / orphan. Integration test that spawns a fake subagent process, kills its parent, runs cleanup, verifies subagent gone — harder, may skip.

---

## 6. Dependencies

- `references/scripts/process_utils.py` — extend or wrap `is_process_alive` for the cleanup.
- `references/scripts/cycle_post.py` — call point.
- `references/scripts/boot_remote.py` — call point.
- `references/scripts/orphan_cleanup.py` (new) — the actual logic.
- Test scaffolding under `tests/test_orphan_cleanup.py` (new).

## 7. Non-Goals

- Upstream fix in Claude Code (separately tracked).
- Killing the parent cmd.exe shim of a real agent — handled by `boot_remote.py` reboot flow already.
- Killing claude.exe processes outside SquidSquad clones — that's the user's own Claude Code IDE / other CLI sessions.
- Reorganizing the process tree (e.g. moving from cmd-shim-based launch to direct claude.exe launch).

## 8. Risks

1. **False positive — kill a real agent by mistake**: highest-impact failure. Mitigation: STRICT identification rule (must match `.claude-pid` parent), default-deny behavior, audit log of every kill decision.
2. **False negative — miss an orphan**: low-impact failure (orphans accumulate slower; manual sweep still works). Acceptable.
3. **Race with respawn**: agent restarts during cleanup; could misidentify mid-respawn state. Mitigation: capture `.claude-pid` value once at cleanup start; treat newly-spawned processes (age < 30s) as live regardless.
4. **Cleanup itself spawns subprocesses on Windows** (via `tasklist` / `taskkill`): these are short-lived and don't add to the orphan count. Acceptable.
5. **Cross-platform consistency**: tasklist semantics on Windows vs `ps`/`pgrep` on POSIX. Use the existing `process_utils.is_process_alive` as a primitive; build higher-level checks on top.

## 9. Next Step

Write CONTEXT-9688.md locking the chosen option (Hybrid A+C) + answers to the 8 open questions. Then human approval gate. Then skill picks up (auto since it's a bug + role:skill).
