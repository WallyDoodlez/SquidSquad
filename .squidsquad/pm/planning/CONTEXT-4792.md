# CONTEXT-4792 — Harness Sole-Authority Lifecycle

**Issue**: #4792 (rescoped from "Deprecate sentinel files" → "Harness sole-authority lifecycle")
**Phase**: 3 (Planning) — Context bundle
**Date**: 2026-05-17 (revised 2026-05-18)
**Author**: pm-lead
**Inputs**: `DECISIONS-4792.md` (Q1–Q17 locks), `RESEARCH-4792-lifecycle-audit.md` (787 lines), `gh issue view 4792 --comments`
**Hard-prereq partner**: #8692 (singleton enforcement — shipped)
**Closes**: #7693 (context-pressure restart). Adjacent: #8689 (restart endpoint latency — shipped).

---

## Revision Log

- **2026-05-18** — Revised per deepseek R1 review + PM-locked RESTARTING scope extension. Force-kill safety net scope now consistently documented across §2 Q7, §3.3, §3.4, §3.6, and §5.1 as `intent ∈ {STOPPING, RESTARTING}`. `.claude-pid` multi-reader clarification applied (Finding 1). §3.6 elapsed-time expression corrected to `time.time() - intent_set_at > 60` (Finding 4). §5.1 `intent_set_at` migration handling now explicitly two-case (legacy vs present) (Finding 5).

---

## 1. Executive Summary

#4792 delivers a **sole-authority lifecycle cleanup**: the harness becomes the
exclusive gatekeeper of agent process start/stop/restart, and every parallel
control path that today silently overrides harness intent is removed. The
rescope (Issue comment 2026-05-17) expanded the original "delete `.stop` and
`.stop-after-cycle`" framing into a full audit-cleanup of the seven scripts
that touch lifecycle: `harness.py`, `boot_remote.py`, `health_check.py`,
`cycle_pre.py`, `cycle_post.py`, `start_team.py`, `reboot_agent.py`.

Per the load-bearing principles repeated throughout this document:

1. **Harness is the sole gatekeeper of agent process lifecycle.** No parallel
   control paths — `boot_remote.py` keeps a library role but loses its CLI;
   `reboot_agent.py` is gutted to two helper functions; `start_team.py`
   becomes a thin shim that calls the canonical operator interface.
2. **Blast-radius minimization.** Preserve current `/loop`-mode byte-identical
   wherever possible. Functions that are still imported by `harness.py`
   (`_kill_process`, `_read_claude_pid`) stay in place; only their `main()`
   wrappers and sentinel-file reads die. `.booting` and `.claude-pid` are
   kept unchanged — they are single-writer mutexes (`.booting` has a
   single reader; `.claude-pid` has multiple readers, per Q14), not
   split-brain control paths (Q9, Q14).
3. **L1–L4 only.** All agent instruction changes flow through compose stack
   fragments (Q12). The instruction-layer fix for #7693 (Q7) is a fragment
   addition under `references/sub-skills/`, then a recompose of all four
   roles.

The work decomposes into **four categories** plus an upgrade-path artifact:

- **(a) Sentinel-file removal** — delete every read/write of `.stop` in
  the seven scripts; delete the vestigial `.restart` and `.health` parsers;
  remove the doc-debt comment for `.stop-after-cycle`. `.claude-pid` and
  `.booting` are explicitly preserved (Q9, Q14, Q16).
- **(b) Operator entry-point convergence** — `squidsquad_cli.py` is
  confirmed canonical (Q1). `start_team.py` becomes a thin shim that
  delegates to `squidsquad_cli`. `boot_remote.py main()` and
  `reboot_agent.py main()` are removed (Q1, Q2, Q3).
- **(c) Trim `reboot_agent.py` and `health_check.py`** — not deleted, only
  trimmed, per blast-radius minimization (Q3 keeps `_kill_process` /
  `_read_claude_pid` as harness imports; Q4 keeps `health_check.py` as the
  offline read-only fallback). Phase 6+ tech-debt items are filed for the
  follow-up renames/deletions.
- **(d) #7693 fix via Q7 mechanism** — agents self-quit via the `/quit`
  slash command after `cycle_post.py` exits 42 (instruction-layer fix in
  L1–L4 fragments), and the harness adds a 60-second force-kill safety net
  for stuck agents whose intent ∈ {STOPPING, RESTARTING} and whose
  `.claude-pid` is still alive (the same stuck-agent failure mode applies
  to both intents).

Plus **upgrade-path artifact**: on first boot after the cleanup ships, the
harness walks `.squidsquad/<role>/` for every configured role and deletes any
leftover `.stop`, `.restart`, and `.health` files (Q13). Self-healing,
idempotent, downgrade-safe (`.harness-state.json` is the authoritative intent
record; legacy sentinels are non-load-bearing parallel paths per Q13).

Finally, the **fragment updates** (Q12): `agent-lifecycle.md` references
`squidsquad_cli.py` as canonical and drops `.health` legacy-fallback mentions;
a new instruction line covers the post-exit-42 `/quit` self-termination. All
four role CLAUDE.md files are recomposed.

---

## 2. Locked Architectural Decisions

Pulled from `DECISIONS-4792.md`. Each lock is summarized in one bullet plus a
one-line "How to apply" for the implementer.

- **Q1 — Operator entry-point: `squidsquad_cli.py` is canonical.**
  How to apply: leave `squidsquad_cli.py` unchanged; rewrite `start_team.py`
  to delegate every command to `squidsquad_cli` semantics (boot, stop,
  reboot — all-roles and per-role); preserve `start_team.py`'s CLI
  surface for operator muscle memory.

- **Q2 — `boot_remote.py` survives as harness-internal library.**
  How to apply: delete `main()`, argparse, and CLI flags. File remains,
  imported only by `harness.py`. Remove all sentinel-file reads
  (`.stop`, `.health`, legacy `.pid`).

- **Q3 — `reboot_agent.py` survives, gutted to helpers.**
  How to apply: keep only `_kill_process` and `_read_claude_pid`. Delete
  `reboot()`, `_kill_and_respawn`, `main()`, the `.stop` read at line 134,
  the `.pid`/`.claude-pid` deletes. File rename to `process_ops.py`
  deferred to Phase 6+.

- **Q4 — `health_check.py` survives as offline-fallback, read-only.**
  How to apply: delete `.stop` read (line 304) and `.health` read
  (line 329). Keep PID-based liveness check only. Add docstring note:
  "offline fallback; prefer GET /status". Caller migration deferred to
  Phase 6+.

- **Q5 — Keep both `POST /agents/{role}/stop` and `POST /agents/all/stop`.**
  How to apply: no harness API change. Web-UI vision (#3963 dependency)
  requires both fan-out and per-role.

- **Q6 — PID-based liveness retained; no heartbeat events in #4792.**
  How to apply: do not touch `update_health` polling cadence; do not add
  heartbeat ingress. Phase 7+ may revisit when #3963 web dashboard arrives.

- **Q7 — #7693 fix: agent self-quit via `/quit` + harness force-kill safety
  net.** Primary: cycle_post exits 42 → L1–L4 fragment instructs agent to
  invoke `/quit`. Safety net: harness force-kills claude PID if
  `intent ∈ {STOPPING, RESTARTING}` for > 60s while `.claude-pid` remains
  alive (per PM lock 2026-05-18 — same stuck-agent failure mode applies
  to both intents; STOPPING leaves the agent stopped after kill,
  RESTARTING respawns it via the normal intent gate).
  How to apply: add fragment instruction line (likely
  `agent-lifecycle.md` or new `graceful-stop.md`); add timeout logic to
  `harness.update_health()` so it tracks "intent set at" and force-kills
  on overrun for either intent.

- **Q8 — No required harness check in `cycle_pre.py`; informational only.**
  How to apply: add a `harness_status: "reachable" | "unreachable"` field
  to `cycle-input.json`. Agents continue working autonomously regardless;
  they may flag the field in their iteration summary.

- **Q9 — `.booting` sentinel kept as harness-internal boot-slot lock.**
  How to apply: do not touch `_write_booting_sentinel`,
  `_has_booting_sentinel`, `_clear_booting_sentinel`. Single writer/reader
  inside `boot_remote`, atomic write, TTL 30s — same shape as
  `.claude-pid`.

- **Q10 — `.harness-state.json` is the sole crash-recovery mechanism.**
  How to apply: no schema change. Test plan covers the six crash scenarios
  enumerated in DECISIONS-4792 Q10. JSON file remains authoritative for
  intent across harness restarts.

- **Q11 — Distribution/packaging audit shipped as test-plan checklist.**
  How to apply: verify `installer-files.txt` and `packages/cli/package.json`
  expose only canonical entry points after cleanup; confirm
  `start_team.py boot` muscle-memory preserved via the shim.

- **Q12 — CLAUDE.md updates flow through compose stack.**
  How to apply: edit `references/sub-skills/common/agent-lifecycle.md`;
  remove `.health` legacy-fallback mentions; run `compose.py deploy-all`
  to regenerate skill, pm, qa, dm CLAUDE.md. Byte-identical /loop
  regression check per role.

- **Q13 — Harness cleans legacy sentinel files on first post-upgrade boot.**
  How to apply: add a one-shot cleanup pass in `harness.py` lifespan
  startup that walks `.squidsquad/<role>/` for every configured role and
  unlinks `.stop`, `.restart`, `.health` if present. Log each removal.
  Idempotent on subsequent boots.

- **Q14 — `.claude-pid` rewrite semantics: out of scope.**
  How to apply: do not touch `thin_launcher._write_pid`,
  `_clear_pid`, `_check_singleton` (the #8692 path). Byte-identical
  regression AC against `thin_launcher.py:66-83`.

- **Q15 — `diagnostics.py`: out of scope.**
  How to apply: zero modifications. Byte-identical regression check.

- **Q16 — Delete stale-file parsers immediately. No backward-compat window.**
  How to apply: remove `.health` parser, `.pid` parser, `.stop` reader,
  `.restart` reader in a single change. Q13's harness-boot cleanup is the
  safety net for any leftover files on disk.

- **Q17 — `start_team.py` primary-vs-clone path bug vanishes with cleanup.**
  How to apply: no special remediation needed — `_write_stop` and
  `_remove_stop` deletions make the bug disappear. Test plan adds a
  primary-vs-clone audit: every sentinel-file write being kept
  (`.claude-pid`, `.booting`) is verified to use the clone path.

---

## 3. Workflow Specification — Lifecycle Paths Post-Cleanup

This section documents the **target** behavior for each lifecycle path after
#4792 ships. Each subsection describes the path step-by-step so the test plan
can derive a TC.

### 3.1 Agent start (boot)

Operator invocation:

```
python references/scripts/squidsquad_cli.py start --all
  → POST /agents/all/start
    → harness loop: boot_remote.boot_agent(role)
        → boot_remote._needs_boot(role)  [reads .claude-pid, .booting ONLY]
        → boot_remote._write_booting_sentinel(role)  [.booting lock — Q9]
        → boot_remote._spawn_terminal(role)
            → subprocess.Popen([wt|cmd|osascript|tmux] ... thin_launcher.py role)
              → thin_launcher._check_singleton()  [Q14 unchanged]
              → thin_launcher._write_pid()        [.claude-pid atomic write]
              → subprocess.Popen(claude, ...)     [parent claude session begins]
        → boot_remote._clear_booting_sentinel(role)
    → state.set_agent(role, intent=running, status=starting, boot_time=...)
    → state.save_state()  [persists to .harness-state.json — Q10]
  → 200 OK
```

No `.stop`, `.restart`, `.health` reads anywhere. `.booting` is the only
"sentinel" file written during boot, and it is harness-internal per Q9.

### 3.2 Agent graceful stop

Operator invocation:

```
python references/scripts/squidsquad_cli.py stop skill
  → POST /agents/skill/stop  [harness.py:1259-1273, unchanged]
    → state.get_agent("skill").intent = STOPPING
    → state.intent_set_at["skill"] = time.time()  [NEW per Q7 — force-kill timeout tracking]
    → state.save_state()
  → 200 OK
```

The harness does NOT write any file and does NOT kill any process. The agent
discovers the intent at its next cycle boundary:

```
(skill agent, next cycle_post.py invocation)
cycle_post._do_stop_after_cycle_check
  → cycle_post._query_harness_intent("skill")
    → GET http://127.0.0.1:7373/agents/skill  [harness.py:868-876]
    → returns intent="stopping"
  → returns True
cycle_post.main → returns 42
```

Per Q7, the agent's L1–L4 instructions (composed into `.squidsquad/skill/CLAUDE.md`
via `agent-lifecycle.md`) include the line:

> After `cycle_post.py` exits 42, immediately invoke `/quit`.

The agent reads cycle_post's exit code from its bash tool output, recognizes
42, and issues `/quit` in its next assistant message. The claude session
terminates cleanly. `thin_launcher.proc.wait()` returns 42, thin_launcher
clears `.claude-pid` and exits.

Harness `update_health` poll (every 5s) sees the agent's PID gone and intent
STOPPING — does NOT respawn (intent gate at `harness.py:248` keeps
auto-reboot inactive when intent ≠ RUNNING/RESTARTING). Marks agent
status=stopped, idle in the table.

### 3.3 Agent force-kill safety net

If the agent does not honor `/quit` (e.g., wedged tool call, missed
instruction, claude bug), the harness force-kills as a safety net. Per Q7
(scope: `intent ∈ {STOPPING, RESTARTING}` per PM lock 2026-05-18):

```
(harness update_health poll, every 5s)
for role in agents:
  if state.intent in (STOPPING, RESTARTING):
    elapsed = time.time() - state.intent_set_at[role]
    if elapsed > 60 and claude_pid_alive(role):
      log.warning(f"agent {role} did not self-quit within 60s — force-killing PID {pid}")
      reboot_agent._kill_process(pid)   # via in-place helper (Q3)
      state.intent_set_at.pop(role, None)
      # Do NOT directly mark status — let the next update_health poll
      # reconcile: STOPPING → stopped (no respawn); RESTARTING → respawn
      # via the existing intent gate in boot_remote.boot_agent().
      state.save_state()
```

Trigger conditions (all three must hold):

1. `state.intent in (STOPPING, RESTARTING)`
2. `.claude-pid` exists and the PID is alive
3. `time.time() - intent_set_at > 60`

After kill:
- `thin_launcher` (if still wrapping claude) observes child exit, clears
  `.claude-pid`, exits.
- `harness.update_health` on the next poll sees PID gone:
  - If `intent == STOPPING`: marks status=stopped, intent stays STOPPING
    (no respawn).
  - If `intent == RESTARTING`: the normal auto-reboot gate fires and
    `boot_remote.boot_agent(role)` respawns the agent (this is the same
    code path that already handles dead-PID-with-RESTARTING-intent
    recovery — the force-kill simply unsticks the case where the
    parent claude session refused to terminate).
- Operator visibility: `GET /status` reports the agent's new status.

The 60-second timeout is **load-bearing** for the #7693 fix because the
existing self-restart mechanism (cycle_post exit 42) does not actually kill
the parent claude session today (Research §5.3, §9.2). The Q7 primary
mechanism (agent self-quits via `/quit`) closes the bug in the happy path;
the 60s timeout closes the residual case where `/quit` doesn't fire. The
same residual failure mode (stuck claude session refusing to honor `/quit`)
applies to RESTARTING intent — the PM lock (2026-05-18) extended the safety
net to both intents so a stuck restart cannot leave an agent permanently
wedged either.

### 3.4 Agent restart

Operator invocation:

```
python references/scripts/squidsquad_cli.py restart skill
  → POST /agents/skill/restart  [harness.py:1276-1347]
    → state.set_agent("skill", intent=RESTARTING)
    → state.intent_set_at["skill"] = time.time()  [NEW per Q7]
    → state.save_state()
    [Idle path, #8689 — current-state startswith "idle" AND .claude-pid alive]:
      → reboot_agent._kill_process(claude_pid)  [via in-place helper, Q3]
      → harness.update_health (within 5s) observes dead PID, intent=RESTARTING
        → boot_remote.boot_agent(role)  [respawn]
    [Queued path, mid-cycle]:
      → agent reaches cycle_post, queries intent, sees RESTARTING → exit 42
      → /quit (per Q7 fragment instruction) → claude exits
      → harness observes PID gone, intent=RESTARTING → respawn
    [Force-kill safety net per Q7 — scope includes RESTARTING per PM lock 2026-05-18]:
      → if neither path fires within 60s of intent_set_at, the §3.3 timer
        force-kills the claude PID. Because intent is RESTARTING, the
        next update_health poll respawns via boot_remote.boot_agent(role).
```

**Removed** from the current implementation (per 5.1 below):
- The `.stop` delete at `harness.py:1297` (no `.stop` file exists post-cleanup).

### 3.5 Operator stop-the-team

Both endpoints preserved per Q5:

```
python references/scripts/squidsquad_cli.py stop --all
  → POST /agents/all/stop  [harness.py:830-865]
    → for role: state.set_agent(role, intent=STOPPING)
                state.intent_set_at[role] = time.time()
    → state.save_state()
  → 200 OK
```

Then, identically to 3.2 / 3.3, each agent observes its intent at its next
cycle boundary, `/quit`s, and the harness force-kill timer is the safety net
for stragglers.

Per-role stop (`squidsquad_cli stop skill`) is the same path scoped to a
single role.

### 3.6 Crash recovery — harness side

If the harness itself crashes (or is killed), state is recovered from
`.harness-state.json` per Q10:

```
harness.py startup (lifespan)
  → state.load_state()  [harness.py:336]
    [reads .harness-state.json — intents, boot_time, last_cycle, intent_set_at, ...]
  → walk .squidsquad/<role>/ for legacy sentinel cleanup per Q13:
      for role in config.agents:
        for name in (".stop", ".restart", ".health"):
          path = clone_root(role) / ".squidsquad" / role / name
          if path.exists():
            log.info(f"upgrade cleanup: removing legacy {name} for {role}")
            path.unlink(missing_ok=True)
  → update_health poll begins
    [observes which PIDs are alive; reconciles state.status]
  → if state.intent[role] == RUNNING and PID dead → boot_remote.boot_agent(role)
  → if state.intent[role] in (STOPPING, RESTARTING) and PID alive
       and `time.time() - intent_set_at > 60`
      → force-kill per 3.3 (STOPPING leaves stopped; RESTARTING respawns
        via the standard intent gate on the following poll)
  → if state.intent[role] == STOPPING and PID dead → leave stopped
  → if state.intent[role] == RESTARTING and PID dead → boot_remote.boot_agent(role)
```

Crash scenarios covered by the test plan (Q10):

1. Harness crash after `POST /stop` set intent — state persists, agent
   still self-quits next cycle, harness resumes monitoring on restart.
2. Harness crash during the 60s force-kill window — on restart, harness
   reads `intent_set_at` from JSON; if `time.time() - intent_set_at > 60`
   and PID still alive, force-kill immediately (applies to both STOPPING
   and RESTARTING intents per PM lock 2026-05-18).
3. Agent crash between intent set and `cycle_post` — harness observes PID
   gone, intent STOPPING → mark stopped, do not respawn.
4. Both simultaneous — agent already dead; harness restart sees PID gone
   with STOPPING → mark stopped.
5. `.harness-state.json` corrupted — harness logs error, refuses to start
   under crash-recovery mode; operator intervention.
6. `.harness-state.json` deleted — defaults restored, intent lost (same as
   fresh install).

### 3.7 Crash recovery — agent side

Agent-side crash recovery is unchanged. On `thin_launcher` start:

```
thin_launcher.py:66-83 _check_singleton  [Q14 byte-identical]
  → if .claude-pid exists and PID alive: exit 3
  → else: write .claude-pid, spawn claude
```

claude reads `working-state.md` to resume mid-task. Next `cycle_pre.py`
invocation queries harness intent (the new informational `harness_status`
field per Q8) but does not gate on it — work proceeds regardless. Eventual
convergence: if intent is STOPPING, the agent will reach `cycle_post`, see
STOPPING via `_query_harness_intent`, exit 42, `/quit`.

There is **no special** crash-recovery logic on the agent side. Per Q8, work
execution does not require a harness handshake.

### 3.8 Upgrade flow

First harness boot after #4792 ships:

```
harness.py lifespan startup (one-shot pass, idempotent):
  for role in agents_from_config():
    for sentinel_name in (".stop", ".restart", ".health"):
      sentinel_path = clone_root(role) / ".squidsquad" / role / sentinel_name
      if sentinel_path.exists():
        log.info(f"#4792 upgrade cleanup: removing {sentinel_path}")
        sentinel_path.unlink(missing_ok=True)
```

Properties:

- **Self-healing**: any leftover legacy sentinels on disk are silently
  removed; the cleanup is not gated on a "have we upgraded yet?" flag.
- **Idempotent**: on subsequent boots the loop runs but finds no files,
  emits nothing visible.
- **Logged**: each removal emits a single info-level log line so the
  upgrade trace appears in the harness log.
- **Downgrade-safe**: if the operator rolls back to a pre-#4792 harness,
  `.harness-state.json` still expresses authoritative intent. Legacy code
  may re-create `.stop`/`.health` files; the next upgrade re-cleans them.
  CHANGELOG note per Q13: "Downgrade safe; legacy sentinel files no
  longer load-bearing."

---

## 4. Scope Boundaries (Out of Scope)

The following are **explicitly excluded** from #4792 to preserve blast-radius
minimization. Each item has a future-task hook so the test plan can confirm
no behavior change.

- **`.claude-pid` rewrite semantics (Q14).** Writer, atomicity, cleanup
  unchanged. Owned by `thin_launcher.py:66-83, 86-101`. Singleton enforcement
  (#8692) gates on this file — must remain byte-identical. Test plan AC:
  diff `thin_launcher.py` `_check_singleton`/`_write_pid`/`_clear_pid` before
  and after #4792 → exactly zero changes.

- **`diagnostics.py` modifications (Q15).** Stays as pure API client. No
  new file reads, no subprocess calls, no direct sentinel touches.
  Byte-identical regression check.

- **`.booting` lock changes (Q9).** Single writer
  (`boot_remote._write_booting_sentinel`), single reader
  (`boot_remote._has_booting_sentinel`), 30s TTL, atomic write. Survives
  harness crash mid-boot. Not split-brain.

- **Liveness mechanism (Q6).** PID polling cadence
  (`harness.HEALTH_POLL_INTERVAL = 5s`) unchanged. No heartbeat-event
  ingress.

- **Event-bus heartbeats** — deferred to Phase 7+, possibly tied to #3963
  Web Dashboard.

- **`reboot_agent.py` rename** to `process_ops.py` — Q3 follow-up,
  Phase 6+ tech debt. File stays at its current name.

- **`health_check.py` deletion and /loop callers migration** — Q4
  follow-up, Phase 6+ tech debt. Callers in PM/QA `cycle_pre` continue
  invoking the script.

These boundaries are load-bearing: violating any of them expands blast
radius beyond what the test plan covers.

---

## 5. Per-Surface Specifications (Cleanup Inventory)

For each file, document the **specific** changes the implementer makes.
File:line references map to the current tree per RESEARCH-4792 §11.

### 5.1 `harness.py`

Changes (in approximate order of appearance):

- **Add force-kill timeout logic** (Q7 safety net, §3.3):
  - Extend `AgentState` (or `HarnessState`) with `intent_set_at: dict[role,
    float]` field, persisted in `.harness-state.json`.
  - Set `intent_set_at[role] = time.time()` in every site that flips intent
    to STOPPING or RESTARTING:
    - `stop_agent(role)` (`harness.py:1259-1273`) — STOPPING
    - `restart_agent(role)` (`harness.py:1276-1347`) — RESTARTING
    - `/agents/all/stop` (`harness.py:830-865`) — loop body, STOPPING
    - `shutdown()` (`harness.py:1350-1427`) — for each role flipped to
      STOPPING
    - `CtrlCHandler._graceful_stop` (`harness.py:1889-1950`) — for each
      role flipped to STOPPING
  - Crash-recovery `load_state` path — explicit two-case handling for
    `intent_set_at` to support both pre-#4792 state files and Q10
    scenario 2:
    - **(a) Legacy state file (intent ∈ {STOPPING, RESTARTING} but no
      `intent_set_at` field present):** this is a pre-#4792 state file
      that did not persist the field. Default
      `intent_set_at[role] = time.time()` so the 60s force-kill window
      begins fresh after the post-upgrade recovery (no clock data exists
      from before the upgrade to honor).
    - **(b) Current state file (`intent_set_at` IS present):** preserve
      it unchanged. The normal `update_health` poll will compute
      `time.time() - intent_set_at` and force-kill immediately if > 60s
      per Q10 scenario 2. Do NOT reset the window — that would
      indefinitely defer the kill on every harness restart.
  - In `update_health()`, after the existing dead-detection loop, add the
    force-kill check (scope: `intent ∈ {STOPPING, RESTARTING}` per PM lock
    2026-05-18):
    ```
    for role, state in self.agents.items():
      if state.intent in (STOPPING, RESTARTING) and self.intent_set_at.get(role):
        elapsed = time.time() - self.intent_set_at[role]
        if elapsed > 60 and _claude_pid_alive(role):
          log.warning(...)
          reboot_agent._kill_process(pid)
          self.intent_set_at.pop(role, None)
          # Do NOT directly mutate status — the next update_health poll
          # observes the dead PID and reconciles per the existing intent
          # gate: STOPPING → stopped; RESTARTING → boot_agent() respawn.
    ```
- **Add legacy-sentinel cleanup on boot** (Q13, §3.8):
  - In lifespan startup, **before** `update_health` first poll, iterate
    configured roles and unlink `.stop`/`.restart`/`.health` per role.
- **Delete `.stop` reads in `update_health`**:
  - `harness.py:239` — drop the `.stop` file check (currently sets
    `status=stopped`).
- **Delete `.stop` delete-on-restart workaround**:
  - `harness.py:1295-1298` — remove
    `stop_file.unlink(missing_ok=True)` (no `.stop` file ever exists
    post-cleanup).
- **Keep**:
  - All HTTP endpoints (Q5 — no API surface change).
  - `reboot_agent._kill_process` / `_read_claude_pid` imports
    (`harness.py:1316, 1320, 1404, 1407`) — Q3 keeps them as helpers.
  - `.harness-state.json` / `.harness-port` / `.event-state.json` writes
    (harness-owned state, not sentinels).

### 5.2 `boot_remote.py`

Changes:

- **Delete `main()` and argparse** — entire CLI surface removed (Q2). File
  becomes import-only.
- **Delete `_has_stop_sentinel`** (`boot_remote.py:181-184`).
- **Delete `.stop` read in `_needs_boot`** (`boot_remote.py:300`). The
  check becomes: PID-alive on `.claude-pid` AND no `.booting` lock → can
  boot.
- **Delete `_read_health_file`** (`boot_remote.py:262-288`).
- **Delete `_read_pid_file`** and the legacy `.pid` fallback in
  `_needs_boot` (`boot_remote.py:141-160, 321-326`) — Q16 immediate
  removal.
- **Delete `_clean_stale_restart`** (`boot_remote.py:245-257`) — Q16.
- **Keep**:
  - `_write_booting_sentinel`, `_has_booting_sentinel`,
    `_clear_booting_sentinel` (`boot_remote.py:211-242`) — Q9.
  - `_is_process_alive`, `_spawn_*` family — needed by harness.
  - `boot_agent`, `boot_all` — primary entry points called by harness.

### 5.3 `reboot_agent.py`

Changes (gut, do not delete):

- **Keep** `_kill_process` (`reboot_agent.py:50-56`).
- **Keep** `_read_claude_pid` (`reboot_agent.py:78-90`).
- **Delete** `reboot()` (`reboot_agent.py:121-183`), including the `.stop`
  read at line 134.
- **Delete** `_kill_and_respawn` (`reboot_agent.py:93-118`).
- **Delete** `main()` and argparse.
- **Delete** `_read_pid_file` (Q16 — legacy `.pid` parser).
- File is left at < 100 lines, functionally a helper module. Phase 6+ task
  renames to `process_ops.py`.

### 5.4 `health_check.py`

Changes (trim, keep file):

- **Delete** `.stop` read at `health_check.py:304`.
- **Delete** `.health` read at `health_check.py:329`.
- **Delete** legacy `.pid` parser (`_read_pid_file`,
  `health_check.py:175`) — Q16.
- **Keep** `.claude-pid` parsing and PID-liveness check — the script
  becomes "thin offline fallback" per Q4.
- **Add docstring note**: `"Offline fallback for human diagnostics. Prefer
  GET /status (squidsquad_cli.py status) when harness is running."`
- File stays at the same path; PM/QA `cycle_pre.py` continues calling it
  via `subprocess.run`. Caller migration deferred to Phase 6+.

### 5.5 `cycle_pre.py`

Changes:

- **Remove** stale `.stop-after-cycle` comment at `cycle_pre.py:676`.
- **Add** `harness_status: "reachable" | "unreachable"` informational
  field to `cycle-input.json` (Q8). Implementation: a single `GET /status`
  HTTP call with short (1–2s) timeout, fail-open. Field used only by the
  agent for self-reporting; not gated on for any decision.
- No functional change to cycle work execution.

### 5.6 `cycle_post.py`

Changes:

- **Delete** `_do_restart_sentinel` (`cycle_post.py:468-483`) — Q16.
  Includes removing the deprecated `restart_needed` field from the
  cycle-output schema reads.
- **Delete** `.stop` write paths in `_do_stop_after_cycle_check`
  (`cycle_post.py:539-575`) — already replaced by HTTP intent query at
  lines 518-536, but tidy up any residual file-write fallbacks.
- **Keep** `_query_harness_intent` (`cycle_post.py:518-536`) — this is
  the canonical HTTP intent check.
- **Keep** `_do_stop_after_cycle_check` (renamed `_check_harness_intent`
  optional, low priority).
- **Keep** `exit 42` semantics (`cycle_post.py:741-743`).
- **Important note for the implementer**: `cycle_post.py` does **NOT**
  kill claude. That is intentional and load-bearing — claude's
  termination is driven by:
  1. Agent reading exit 42 from bash tool output, then invoking `/quit`
     per the L1–L4 fragment instruction (Q7 primary mechanism, fragment
     in §5.11 below).
  2. Harness force-kill timeout (Q7 safety net, §5.1).
  This split keeps "harness is sole-authority" intact — the harness kills
  via the 60s timeout; the agent's own `/quit` is the cooperative path.

### 5.7 `start_team.py`

Changes (refactor to thin shim):

- **Delete** `_write_stop` (`start_team.py:74-80`) — Q17, the path-bug
  function vanishes.
- **Delete** `_remove_stop` (`start_team.py:83-87`).
- **Delete** `_clean_stale_sentinels` (`start_team.py:90-95`).
- **Rewrite** `cmd_boot` (`start_team.py:114-124`) — instead of calling
  `boot_remote.boot_agent` directly, call
  `squidsquad_cli.cmd_start([role])` (or equivalent function-level
  delegate).
- **Rewrite** `cmd_reboot` (`start_team.py:127-166`) — delegate to
  `squidsquad_cli.cmd_restart`. Delete the `--force` fallback that
  invokes `reboot_agent._kill_process` directly (the harness `/restart`
  endpoint handles idle-kill per #8689 and the new force-kill timeout
  per Q7 covers stuck cases).
- **Rewrite** `cmd_stop` (`start_team.py:169-179`) — delegate to
  `squidsquad_cli.cmd_stop`. Delete the `.stop` write fallback.
- **Preserve** the CLI surface flags (`--all`, `--role`, `--stop`,
  `--reboot`, `--force`) so operator muscle memory continues to work
  (Q11).
- End state: ~50 lines, pure delegation.

### 5.8 `squidsquad_cli.py`

Changes:

- **Confirmed canonical** (Q1) — no changes are mandatory.
- **Possible additions**: if `start_team.py` exposes any operator command
  that `squidsquad_cli.py` does not yet (e.g., a specific `--reboot
  --force` flag), add the missing command/flag so the shim has
  something to delegate to. Audit this in implementation Phase 3
  (sequencing §9 below).

### 5.9 `references/sub-skills/common/agent-lifecycle.md`

Source fragment — edited, then composed into role CLAUDE.md via
`compose.py deploy-all`.

Changes:

- Replace all `start_team.py` direct-CLI references with
  `squidsquad_cli.py` as canonical (Q1). Keep a single mention that
  `start_team.py <args>` is a backward-compatible shim.
- Remove `.health` legacy-fallback mentions (Q12). Search-and-replace:
  - `"PID monitoring (primary), \`.health\` file (legacy fallback)"` →
    `"PID monitoring via \`.claude-pid\` (sole liveness signal)"`.
- Remove `.stop` / `.restart` / `.stop-after-cycle` documentation
  references — these files no longer exist.
- Update the "lifecycle interface" code block to show
  `squidsquad_cli.py` commands instead of `start_team.py`.

### 5.10 Role-specific CLAUDE.md (composed)

These are the **composed output files**, regenerated from fragment edits in
§5.9 via `compose.py deploy-all`. Per Q12, do not edit directly.

Specific stale strings to be eliminated (RESEARCH §12 line refs):

- `references/roles/skill/CLAUDE.md` (composed: skill 1411) — `.health`
  legacy-fallback mention removed.
- `references/roles/pm/CLAUDE.md` (composed: pm 1979) — same.
- `references/roles/qa/CLAUDE.md` (composed: qa 1174) — same.
- `references/roles/dm/CLAUDE.md` (composed: dm 1087) — same.

After fragment edits in §5.9, run:

```
python references/scripts/compose.py deploy-all
```

Then byte-diff each `.squidsquad/<role>/CLAUDE.md` against the prior
composed version. Expected diff: only the lines that changed in fragments.
Any unexpected diff is a compose regression.

### 5.11 L1–L4 fragment additions (Q7 instruction layer)

Add the post-exit-42 self-quit instruction. Per Q12, the addition goes into
a compose-stack fragment, not a role-specific file. Two options for
placement (implementer choice based on minimal blast radius):

- **Option A**: Append to existing
  `references/sub-skills/common/agent-lifecycle.md` under a new
  subsection "Graceful Stop — Self-Quit Protocol".
- **Option B**: Create a new fragment
  `references/sub-skills/common/graceful-stop.md` and include in all four
  role `includes.yml`.

Recommended (lower blast radius): Option A.

Instruction line (suggested wording — implementer may refine):

> **After `cycle_post.py` exits with code 42** (graceful stop or
> restart signaled by harness), immediately invoke the `/quit` slash
> command to terminate the claude session. The harness will then observe
> the process exit and either mark you stopped or respawn you per its
> intent state machine. Do NOT continue working after a 42 exit — the
> harness is waiting for you to terminate.

Applies to all four roles (skill, pm, qa, dm) — graceful stop is
role-agnostic. Recompose all four roles after the fragment edit.

---

## 6. Coordination with Phase 5 (#7630)

#4792 lives next to the Phase 5 event-driven bundle. The interactions:

- **#4792 + #8692 together** gate any per-role flip of `event-driven: yes`.
  Both must ship before any role's config flips. Per the rescope comment:
  "Without sole-authority, the bundle-shipped event mode would still have
  split-brain lifecycle risk."
- **#4792 does NOT block Phase 5 bundle implementation.** The bundle
  (#8694, #8700, #8704, #8697) ships in /loop mode; flipping any role to
  event-driven is the gated step.
- **#4792 + #8697 coordination** (compose dual-mode):
  - **If #8697 ships first** (compose stack supports `common-loop/` and
    `common-events/` trees): #4792's fragment edits in §5.9 / §5.11 apply
    to BOTH trees. The cleaned `agent-lifecycle.md` is duplicated into
    both directories.
  - **If #4792 ships first**: #8697 migrates the cleaned fragment content
    forward when it splits the tree.
  Either order is workable; the implementer picks the path that minimizes
  rework based on actual merge order.

---

## 7. Hard Prerequisite Status

#4792 itself has **no hard prerequisites**.

Adjacent dependencies:

- **#8692 (singleton enforcement)** — shipped. SIBLING hard prereq for
  the event-mode flip, NOT a #4792 prereq. #4792 preserves `.claude-pid`
  semantics per Q14 so #8692 keeps working.
- **#4966 (harness FastAPI)** — shipped. The HTTP API surface #4792
  relies on.
- **#8689 (restart endpoint latency)** — shipped. The idle-path
  immediate-kill is the foundation that #4792's force-kill safety net
  extends.

---

## 8. Bug Closures Triggered

### 8.1 #7693 — context-pressure restart does not respawn agent (CLOSES)

Closure mechanism: **Q7 dual mechanism (§5.11 + §3.3)**.

Root cause per Research §5.3 and §9.2: `cycle_post.py` exit code 42 is a
bash subprocess exit, not a claude exit. The parent claude session never
dies. The harness `update_health` therefore never observes a dead PID and
never respawns.

Fix:
- Primary (§5.11): agent instruction-layer fragment adds the `/quit`
  invocation after exit 42 — claude actually terminates.
- Safety net (§3.3, §5.1): if the agent fails to `/quit` within 60s of
  intent set, harness force-kills.

Test plan TC: trigger context pressure, verify claude exits within 60s
(happy path < 5s via `/quit`; degraded path < 60s via force-kill). Verify
harness respawns post-exit.

### 8.2 #8689 — restart endpoint idle agent delay (ADJACENT)

Status: already shipped. The idle-path immediate-kill at
`harness.py:1295-1347` covers most cases. The new 60s force-kill timeout
(§3.3) **may** close a residual non-idle case if the restart endpoint
fails to kick the agent into exit-42. Closure mechanism if applicable:
same Q7 safety net.

The test plan should include a regression TC: `POST /restart` on an
agent that is mid-cycle but not stuck → verify it follows the queued
path and respawns within one cycle boundary without the 60s timer
firing.

---

## 9. Sequencing / Implementation Order

Suggested phasing — each phase is a coherent PR/branch. Phases 1–5 sum to
the full #4792 ship.

### Phase 1 — #7693 fix (force-kill timeout + self-quit instruction)

Implementer touches `harness.py` (force-kill logic, `intent_set_at` field,
crash-recovery handling) and `references/sub-skills/common/agent-lifecycle.md`
(self-quit fragment). Recompose all four roles.

Tests: TC for #7693 closure (§8.1). TC for §3.3 force-kill trigger
conditions. TC for §3.6 scenario 2 (harness crash during force-kill
window).

This phase alone closes #7693 — operator visibility for the most-asked-for
fix is immediate.

### Phase 2 — Sentinel cleanup in scripts

Implementer touches `harness.py` (remaining 5.1 items), `boot_remote.py`
(§5.2 except CLI removal), `reboot_agent.py` (§5.3), `health_check.py`
(§5.4), `cycle_pre.py` (§5.5), `cycle_post.py` (§5.6).

Tests: byte-diff regression checks per Q11/Q14/Q15. TC for sentinel
absence (TC asserts no script reads `.stop`/`.health`/`.restart` per
grep). TC for §3.1 / §3.2 / §3.4 happy paths with no sentinel files
present.

### Phase 3 — Operator entry-point convergence

Implementer touches `start_team.py` (§5.7) and `squidsquad_cli.py` (§5.8
audit for missing flags). `boot_remote.py main()` removed per §5.2.
`reboot_agent.py main()` removed per §5.3.

Tests: TC for shim parity — every flag combination on `start_team.py`
produces identical observable behavior to its `squidsquad_cli.py`
equivalent. TC for installer manifest (Q11).

### Phase 4 — Fragment edits + recompose

Implementer touches `references/sub-skills/common/agent-lifecycle.md`
(§5.9 — note: Phase 1 already added the self-quit fragment per §5.11),
then runs `compose.py deploy-all`. Verifies role CLAUDE.md byte diffs in
§5.10 contain only expected changes.

Tests: comprehension question (per CQ standard) — fresh agent reads
composed CLAUDE.md, must correctly answer "what does the harness use as
the sole liveness signal?" → expected answer: `.claude-pid`. Verifies the
`.health` legacy mention is fully scrubbed.

### Phase 5 — Upgrade-path cleanup logic

Implementer adds the harness boot-time legacy-sentinel cleanup per §3.8.
This is small and additive; sequenced last so the test plan can run
upgrade scenarios with leftover sentinel files in place.

Tests: TC for §3.8 idempotence (run twice, second pass logs nothing).
TC for §3.8 with stale `.stop` / `.health` / `.restart` files seeded
across all four role directories.

---

## 10. Open Questions

All 17 questions closed in `DECISIONS-4792.md`. The following are
**residual Phase 6+ tech-debt** items captured for traceability but
explicitly out of #4792 scope (per §4):

- Rename `reboot_agent.py` → `process_ops.py` and consolidate other
  process utilities (Q3 follow-up).
- Migrate PM/QA /loop `cycle_pre` health-check callers to a thin
  `GET /status` helper, then delete `health_check.py` entirely
  (Q4 follow-up).
- Add event-bus heartbeats for application-layer hang detection
  (Phase 7+, possibly tied to #3963 Web Dashboard).

No residual open questions block implementation. The implementer should
flag any new ambiguity discovered during Phase 1 (e.g., subtleties in
the `intent_set_at` crash-recovery defaulting per §5.1) back to PM via
issue comment before proceeding.

---

## 11. Glossary

Terms used throughout this document, for the test-plan author and
implementer:

- **Sole-authority** — the harness as the exclusive controller of agent
  process start, stop, restart. No parallel control paths.
- **Sentinel file** — a file on disk used as a control-path signal
  between two or more actors, where multiple actors read or write to
  coordinate (contrast with single-writer/reader mutexes like
  `.claude-pid` or `.booting`).
- **Split-brain** — two actors writing or reading the same control
  signal independently, leading to silent disagreement. The root cause
  being eliminated by #4792.
- **Force-kill timeout** — Q7 safety net: 60 seconds after intent set
  to STOPPING (or RESTARTING), if `.claude-pid` is still alive, the
  harness force-kills the claude PID.
- **Self-quit** — the agent invoking `/quit` in response to
  `cycle_post.py` exit 42 (the canonical cooperative termination path
  per Q7).
- **Legacy sentinel** — `.stop`, `.restart`, `.health` — the files
  being removed from the seven scripts and cleaned up on first harness
  boot post-upgrade.
- **Harness-internal** — a file or function owned exclusively by
  `harness.py` (or its tightly-coupled helper `boot_remote.py`) and
  not exposed to operators or other scripts.
- **/loop regression** — a byte-identical check that current
  `/loop`-mode (cycle_pre → creative → cycle_post) behavior is
  preserved through the cleanup. Key sites:
  `thin_launcher.py:66-101`, `cycle_pre.py` non-comment behavior,
  `cycle_post.py` exit-42 semantics.
- **`.booting`** — boot-slot lock owned by `boot_remote`, single
  writer/reader, atomic write, TTL 30s. Kept per Q9.
- **`.claude-pid`** — singleton-enforcement and liveness signal owned
  by `thin_launcher`, single writer (atomic), multiple readers. Kept
  unchanged per Q14.
- **`.harness-state.json`** — sole crash-recovery mechanism for intent
  (Q10). Harness reads on startup, writes on every intent change.
- **`intent_set_at`** — new persisted dict added in §5.1 mapping role
  → timestamp when intent was last flipped to STOPPING or RESTARTING.
  Drives the 60s force-kill window per Q7.
- **Upgrade cleanup** — the one-shot legacy-sentinel removal pass in
  harness lifespan startup (§3.8). Idempotent.
- **Sub-skill fragment** — a markdown file under `references/sub-skills/`
  that is composed into role-specific `CLAUDE.md` via
  `compose.py deploy`. Per Q12, all instruction changes flow through
  fragments, never direct role-CLAUDE.md edits.

---

## End of CONTEXT-4792.md

Faithful to the locks in `DECISIONS-4792.md`. No new design choices
introduced; any ambiguity surfaced during implementation should round-trip
back to PM via issue comment before proceeding.
