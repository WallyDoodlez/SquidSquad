Now I have all the data. Let me compile the complete audit.

```markdown
# audit-AR-86-83 Research — §8.6.1 Periodic Driver & §8.3 Backstop Consistency Audit

## Summary
This audit examines two arch-doc changes authored for `docs/AGENT-RUNTIME.md`: (A) §8.6.1 "The event-mode periodic driver (idle-work scheduler)" — which is **already in the file** at lines 1110–1128, including the updated §8.6 flowchart (lines 1073–1098); and (B) a proposed new subsection in §8.3 "Comment-only handoffs and the pipeline-sentinel backstop" — which is **not yet merged** (authored in PR #12507, per `.squidsquad/pm/working-state.md` line 13 and `.squidsquad/qa/iterations/iter-238.md` line 3).

The audit found **3 ERRORS** (two cross-document contradictions, one pre-existing stale §8.2 reference amplified by adjacency), **4 WARNINGS** (missing config key, sub-skill contradiction requiring edit, format drift, implementation gap), and **3 LOW** items (minor annotation nits, known-deferred reference noted as instructed). The highest-risk overlap — §8.6.1 periodic driver vs HARNESS-ARCH §15 liveness model — is resolved: they are **complementary** (improvement-work scheduling vs liveness detection), but AGENT-RUNTIME §8.2's callout referencing "event_poll idle-ticks" is **stale** against the current HARNESS-ARCH §15 model (the concept was removed in v13–v15 revisions). §8.6.1 does not introduce a new conflict here; it does amplify an existing terminology gap worth closing.

**Recommendation**: Feasible with caveats — 2 errors require config-file and sub-skill edits before merge; 1 stale cross-ref should be resolved in the same change to avoid compounding drift.

## Vault Context
- **BRIEFING.md priorities**: **#12506** (improvement subloop dormant) is the issue §8.6.1 fixes — marked `high, skill` in PM working-state (`.squidsquad/pm/working-state.md` line 15). **#12493** (pipeline-sentinel halt detection) is the issue §8.3 backstop enables — `approved, skill`, gated on this arch landing (line 13). **#12271** (harness liveness redesign) is IN MOTION with slices 1–2 shipped — the AGENT-RUNTIME §8.2 callout reflects an intermediate state of that design.
- **Related decisions**: [[decision-improvement-loop-philosophy]] — the improvement scan as proactive discovery layer; §8.6.1's bounded-burst design preserves the philosophy (idle-time improvement) while fixing the dormancy bug. [[decision-self-healing-sentinel]] — two-tier self-healing (unstick + root-cause) that the §8.3 backstop extends to comment-only-handoff stalls.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — §8.6.1's cron-based driver is deterministic, consistent with the human preference that "cyclic work needs to be programmed deterministically."
- **Human preferences**: `human-profile.md` line 34: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" — the periodic driver (§8.6.1) satisfies this (cron, not LLM-decided). Line 33: "prefers direct/mechanical checks" — the driver's scan-counter + cancel is mechanical.
- **Related learnings**: [[learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter]] — the same "one-shot delivery to poll-less consumer = starvation" shape that #12442 fixed for EAD handoffs is the exact shape #12506 diagnosed for improvement subloops (event_poll never fires idle ticks → no one re-enters the loop → subloop dormant). §8.6.1's bounded-burst driver mirrors the re-emit pattern: lazy arm, bounded count, re-arm on fresh activity.

## Impact Analysis
- **Files touched**: `docs/AGENT-RUNTIME.md` §8.3 (new backstop subsection), §8.6 (flowchart updated), §8.6.1 (new); `references/sub-skills/common-events/idle-cooldown-loop.md` step 5 (must be edited); `.squidsquad/config.md` (must add `Idle Scan Burst` key); possibly `references/sub-skills/common-events/comment-handling.md` (cross-ref update).
- **Behavior changes**: Event-mode agents gain a periodic self-wake mechanism for idle improvement work; PM's pipeline sentinel gains explicit responsibility for detecting comment-only-handoff halts.
- **Dependencies**: §8.6.1 implementation depends on this arch-doc landing (#12506 fix); §8.3 backstop implementation (#12493) is **gated** on the backstop subsection landing first.

## Side Effects
- **Risk 1**: The periodic driver doubles as a "safety-net against a missed nudge" (§8.6.1 line 1119) — this may mask real EAD delivery bugs by making missed nudges self-healing within 30m. Not a correctness problem (idempotent), but could hide regressions in the #12442 bounded-re-emit path. — Severity: L — Mitigation: Document that the driver's forge-read is a safety net, not a replacement for EAD delivery; EAD delivery should still be monitored.
- **Risk 2**: The driver's cron coexists with the persistent Monitor in one Claude Code session. Claude Code's cron (`/loop`) and Monitor tool interaction is not documented in AGENT-RUNTIME — there is no evidence of conflict (Monitor is stdin-based, cron is timer-based), but the combination is novel. — Severity: M — Mitigation: Explicitly state in §8.6.1 that the driver's cron fires independently of Monitor and that both wake sources feed the same §8.1 loop entry point.

## Edge Cases
- **Agent boots directly into work (initial drain non-empty)**: §8.6.1 says driver arms on "first idle/drained state" — correct. The boot drain (§8.2 step 4) processes events first; only after the queue drains does the agent reach idle and arm the driver. No premature scheduling.
- **Driver tick arrives during forge work after a long idle**: The tick fires, the agent notes it, the current work finishes, the next loop iteration does a forge-read (absorbing any work) then checks drain + throttle. Consistent with §8.5 mid-cycle nudge handling.
- **Agent is idle for exactly one throttle window, driver fires, throttle check passes, scan runs, scan_count=1, loop continues, re-check finds queue still empty, throttle NOT elapsed (just ran), driver tick won't fire again for ~30m**: The agent idles. On the next driver tick (~30m later), throttle IS elapsed, scan runs, scan_count=2. After 3 scans (90m of continuous idle), driver cancels. Correct behavior.
- **Forge work arrives after 1 scan, agent processes it, goes idle again**: Driver re-arms with scan_count=0 per §8.6.1 "re-arm" rule. Correct — fresh idle period resets the burst counter.

## Integration Risks
- **§8.6.1 periodic driver vs HARNESS-ARCH §15 liveness heartbeat**: The driver's cron ticks produce tool calls (forge-read, subloop work) which generate `PostToolUse` hooks → §15 activity heartbeats. So the driver actually **generates** liveness signals during idle periods — a positive interaction, not a conflict. However, if the driver cancels after the burst (3 scans), the agent goes truly idle with no tool calls → no heartbeats. Under §15's "after dispatch, no activity AND no hook explaining the silence → dead" rule, this is fine because an idle agent with no dispatched work is not actively monitored (§15.1 line 554). No conflict.
- **Terminology collision risk**: §8.2 callout (line 903) references "`event_poll` idle-ticks" as a liveness signal — a concept removed from HARNESS-ARCH §15 in v13–v15. §8.6.1 introduces a "periodic driver" that fires on a timer, but it is **not** related to the removed "idle-ticks" concept. The stale §8.2 reference could cause readers to conflate the two. Flagged as ERROR-3 below.

## Upgrade & Migration
- **New config values**: `Idle Scan Burst` (default `3`) — must be added to `.squidsquad/config.md` under `## Improvement Scanning` (or a new section). Currently **missing** — flagged as ERROR-2.
- **New files**: None (doc-only change; implementation may add files later).
- **Template changes**: `idle-cooldown-loop.md` step 5 must be edited (see ERROR-1). `comment-handling.md` may need a cross-ref to the §8.3 backstop (LOW).
- **Upgrade steps**: For existing installs, add `Idle Scan Burst: 3` to `.squidsquad/config.md` under `## Improvement Scanning`. No agent restart required (config read is per-cycle).
- **Graceful degradation**: If `Idle Scan Burst` key is missing, agent should default to 3 (per §8.6.1's documented default). The config key makes the default overridable; its absence is non-fatal.

## Open Questions
- **Q1**: Should the driver's cron cadence be independently configurable from the improvement-scan throttle? Currently §8.6.1 ties them together ("at the throttle cadence ≈ cool-down, default 30m") — but a driver that fires at 30m with a 30m throttle means every tick finds the throttle elapsed. Decoupling them (e.g., driver at 10m, throttle at 30m) would let the agent discover forge work sooner after idle. — **Why**: Affects improvement-scan latency and whether the driver's safety-net function (forge-read on tick) is fast enough to matter.

## Recommendation
**Feasible with caveats** — the §8.6.1 content is internally consistent and the §8.3 backstop proposal is consistent with comment-handling.md. Two errors require concrete edits before merge: (1) `idle-cooldown-loop.md` step 5 must be rewritten to name the periodic driver instead of claiming Monitor delivers cadence; (2) `config.md` must add an `Idle Scan Burst` key. The stale §8.2 cross-ref to HARNESS-ARCH §15 should be scrubbed in the same change. The 4 warnings are minor and can be addressed post-merge.

## Findings

### ERRORS

---

**ERROR-1**: `idle-cooldown-loop.md` step 5 contradicts §8.6.1 — sub-skill assumes Monitor delivers periodic cadence

- **Location**: `references/sub-skills/common-events/idle-cooldown-loop.md` line 45 vs `docs/AGENT-RUNTIME.md` lines 1112–1118 (§8.6.1)
- **Contradiction**: The sub-skill states:
  > "The persistent Monitor (see [[event-mode-contract]] "How You Listen") delivers `NUDGE` wake signals at a short fixed cadence"

  This is the **exact assumption #12506 proved false**. `event_poll` emits a NUDGE only on forge events — it is silent on empty polls. An idle event-mode agent (zero forge events) receives NO nudges and thus never re-enters the loop. §8.6.1 explicitly documents this:
  > "`event_poll` emits a NUDGE only on *forge events* (it is silent on an empty poll). So a genuinely idle event-mode agent (zero forge events) never re-enters the loop"

  §8.6.1 line 1125 further states:
  > "The `idle-cooldown-loop` sub-skill's step-5 assumption … is corrected to name this driver as the cadence source — that sub-skill edit is part of the implementation."

- **Fix**: Rewrite `idle-cooldown-loop.md` step 5 to:
  1. Remove the claim that Monitor delivers wake signals at a fixed cadence.
  2. State that in event mode, idle re-entry is driven by the periodic driver (cron/`/loop`) described in AGENT-RUNTIME §8.6.1, NOT by Monitor/event_poll.
  3. Preserve the "if NUDGE arrives" branch (Monitor still delivers forge-event nudges) as an orthogonal wake source.
  4. Preserve the cool-down eligibility check unchanged (the driver tick re-enters the same check).

---

**ERROR-2**: `config.md` missing `Idle Scan Burst` key — referenced as configurable in §8.6.1

- **Location**: `docs/AGENT-RUNTIME.md` line 1123 (§8.6.1) vs `.squidsquad/config.md` lines 61–64 (`## Improvement Scanning` section)
- **Contradiction**: §8.6.1 specifies:
  > "when the count reaches the configured threshold (`Idle Scan Burst`, default 3)"

  The `Idle Scan Burst` key does **not exist** anywhere in `.squidsquad/config.md`. The `## Improvement Scanning` section contains only:
  ```
  - **Enabled**: yes
  - **Improvement Scan Cool-Down**: 30
  ```

  No `Idle Scan Burst` key. The flowchart at AGENT-RUNTIME line 1080 also references `Idle Scan Burst` as a configurable threshold, confirming it is intended to be config-managed.

  Additionally, `idle-cooldown-loop.md` lines 65–71 describe the cool-down configuration but make no mention of a burst cap — adding `Idle Scan Burst` to config.md should be mirrored by an update to that sub-skill's "Cool-Down Configuration" section.

- **Fix**: 
  1. Add `- **Idle Scan Burst**: 3` to `.squidsquad/config.md` under `## Improvement Scanning` (after `Improvement Scan Cool-Down: 30`).
  2. Update `idle-cooldown-loop.md` "Cool-Down Configuration" section (lines 63–71) to document the `Idle Scan Burst` key with its default and semantics.

---

**ERROR-3**: AGENT-RUNTIME §8.2 callout (line 903) references "event_poll idle-ticks" as a liveness signal — concept removed from HARNESS-ARCH §15

- **Location**: `docs/AGENT-RUNTIME.md` line 903 (§8.2 callout) vs `docs/HARNESS-ARCH.md` lines 550–561 (§15.1 current model)
- **Contradiction**: AGENT-RUNTIME §8.2 states:
  > "A proposed redesign replaces PID-liveness with **progress signals emitted by the agent's real loop** — `SessionStart` / `Pre`+`PostToolUse` / `Stop` / `SessionEnd` claude-code hooks plus `event_poll` idle-ticks and acks"

  But HARNESS-ARCH §15.1 (the current locked model, v15+) has **no** `event_poll` idle-ticks. The model is "activity heartbeat + pause-aware guard" where the heartbeat sources are `PostToolUse`/`PostToolUseFailure` hooks and `cycle_post`. The `event_poll` idle-ticks concept existed in HARNESS-ARCH v6 (§15 revision log, line 687) but was removed as redundant in v13–v15 when the model simplified to "activity heartbeat." The HARNESS-ARCH §15 revision log confirms:
  - v6 (line 687): included "`event_poll` idle-ticks + acks"
  - v14 (line 679): "Removed as redundant — … the multi-signal `last_seen` table (SessionStart / event_poll-ticks / ack-cursor as liveness inputs)"
  - v15 (line 678): "Dropped the pong / harness-ping and the L1 ping-priority rule entirely"

  The AGENT-RUNTIME §8.2 callout now points to a stale snapshot of the §15 design. While this is **pre-existing drift** (not caused by §8.6.1), the §8.6.1 change introduces a new "periodic driver" concept in the same §8 section — a reader encountering both the stale "event_poll idle-ticks" reference and the new "periodic driver" could conflate them, compounding the confusion.

- **Fix**: Rewrite AGENT-RUNTIME §8.2 line 903 to match the current HARNESS-ARCH §15.1 model:
  > "A proposed redesign replaces PID-liveness with **progress signals emitted by the agent's real loop** — `SessionStart` / `Pre`+`PostToolUse` / `Stop` / `SessionEnd` claude-code hooks plus `cycle_post` heartbeats — with a pause-aware guard (`PreToolUse` in-flight, `Notification`, `StopFailure`, `PreCompact`), demoting PID to teardown-only."

  Remove "`event_poll` idle-ticks and acks" from the list. The acks (`ack-cursor`) are delivery-confirmation, not liveness signals (per §5.1 Principle 4 / D4 separation).

---

### WARNINGS

---

**WARNING-1**: `config.md` cool-down value is unitless (`30`) while sub-skill and arch-doc use `30m` — format ambiguity

- **Location**: `.squidsquad/config.md` line 64 (`Improvement Scan Cool-Down: 30`) vs `references/sub-skills/common-events/idle-cooldown-loop.md` line 68 (`Improvement Scan Cool-Down: 30m`) vs `docs/AGENT-RUNTIME.md` line 1100 (§8.6: "default 30") vs line 1114 (§8.6.1: "default 30m")
- **Drift**: Three different representations of the same value across four locations:
  | Source | Value | Has unit? |
  |---|---|---|
  | `config.md` | `30` | No |
  | `idle-cooldown-loop.md` line 68 | `30m` | Yes |
  | AGENT-RUNTIME §8.6 line 1100 | `30` (implied minutes) | No |
  | AGENT-RUNTIME §8.6.1 line 1114 | `30m` | Yes |
  
  The unit is unambiguously minutes everywhere (context + §8.6 "matching the old `/loop` cadence" where the `/loop` is `30m` per §7.2 / config `Iteration Interval > Minutes: 30`). But the inconsistency means a parser or future config reader must infer units.

- **Fix**: Add the `m` suffix to `config.md` line 64: `- **Improvement Scan Cool-Down**: 30m`. This matches the `idle-cooldown-loop.md` representation and the `Iteration Interval > Minutes: 30` convention (which separates the unit into the key name rather than the value — but the cool-down key embeds no unit in its name, so the value should carry it).

---

**WARNING-2**: `idle-cooldown-loop.md` step-5 edit is declared as "part of the implementation" in §8.6.1 but not yet done — implementation gap

- **Location**: `docs/AGENT-RUNTIME.md` line 1125 (§8.6.1 "Reconciliations") vs `references/sub-skills/common-events/idle-cooldown-loop.md` lines 44–46
- **Drift**: §8.6.1 states:
  > "The `idle-cooldown-loop` sub-skill's step-5 assumption … is corrected to name this driver as the cadence source — that sub-skill edit is part of the implementation."
  
  The sub-skill edit has **not been made** in the file as audited. If §8.6.1 is merged before the sub-skill edit, agents reading `idle-cooldown-loop.md` will still see the false "Monitor delivers cadence" claim. The arch-doc and sub-skill would be inconsistent at merge time.

- **Fix**: Either (a) bundle the `idle-cooldown-loop.md` step-5 edit in the same PR as the §8.6.1 arch-doc change, or (b) add a conspicuous "**Implementation note:** the companion sub-skill edit in `idle-cooldown-loop.md` step 5 is tracked in #XXXXX and must land before #12506 is closed" to §8.6.1. Option (a) is strongly preferred — the arch-doc should not declare a reconciliation that doesn't exist yet.

---

**WARNING-3**: §8.3 backstop subsection is referenced as authored but does not exist in the file — gated behind PR #12507

- **Location**: `docs/AGENT-RUNTIME.md` §8.3 (ends at line 1040, no backstop subsection present) vs `.squidsquad/pm/working-state.md` line 13 (references PR #12507) and `.squidsquad/qa/iterations/iter-238.md` line 3
- **Drift**: The audit task describes a "NEW subsection in §8.3 'Comment-only handoffs and the pipeline-sentinel backstop'" as authored. The content is described in `.squidsquad/pm/planning/sentinel-halt-body.md` and referenced in working-state, but it is **not present** in the current `docs/AGENT-RUNTIME.md`. It exists in PR #12507 (per the working-state notes). The audit of this subsection is therefore against its described content, not against merged text.
- **Fix**: Confirm PR #12507 contains the backstop subsection. When merged, verify the following consistency properties hold:
  1. The backstop must cross-reference `comment-handling.md` (which already states "Comments are NOT standalone event triggers" at line 8 and "Transition-On-Handoff Rule" at lines 32–34).
  2. The backstop's claim "EAD polls forge state, not comment bodies" must be consistent with AGENT-RUNTIME §5.4 lines 425–438 (EAD polling rules: status label changes, new human comments → PM, PR state changes — EAD does NOT parse comment bodies for handoff semantics).
  3. The backstop's assignment of pipeline-sentinel as "a PM responsibility" must be consistent with §8.6 line 1103 (pm subloop = "pipeline sentinel + improvement scan").
  4. The backstop should note the known deferred: `/work/assign` endpoint fiction (#12495) — per the KNOWN/DEFERRED instruction in the audit task.

---

**WARNING-4**: §8.6.1 claims "No harness change is required" — but the cron scheduling primitive (`/loop`) in event mode alongside persistent Monitor is a novel combination not explicitly tested

- **Location**: `docs/AGENT-RUNTIME.md` line 1121 (§8.6.1)
- **Drift**: The claim is architecturally sound (cron is Claude Code runtime-side, harness-agnostic). However, no test or documentation exists for running both a persistent Monitor AND a `/loop` cron in the same Claude Code session. The BRIEFING.md line 93 notes the live install runs "HYBRID" mode with some agents on EVENT and qa on LOOP — but no agent runs both simultaneously. The interaction between cron ticks and Monitor stdin in a single session is untested.
- **Fix**: Add a brief "Interaction note" to §8.6.1: "The cron and Monitor coexist in one Claude Code session; cron fires are handled as Claude Code tool invocations (not stdin), so they do not race with Monitor NUDGE delivery. A cron tick arriving mid-tool-call is queued by the Claude Code runtime exactly like any other scheduled command." This is low-risk (both are Claude Code built-ins) but documentation coverage is warranted.

---

### LOW

---

**LOW-1**: §8.6 cadence notation — "default 30" vs §8.6.1 "default 30m"

- **Location**: `docs/AGENT-RUNTIME.md` line 1100 (§8.6: "default 30, matching the old `/loop` cadence") vs line 1114 (§8.6.1: "default 30m")
- **Issue**: §8.6 omits the unit suffix on `30` while §8.6.1 includes it. Both mean 30 minutes, but the inconsistency within the same section is a minor polish item.
- **Fix**: Add `m` to §8.6 line 1100: `default 30m`.

---

**LOW-2**: §8.6.1 "≈ the cool-down" — approximate sign when the driver cadence IS exactly the cool-down

- **Location**: `docs/AGENT-RUNTIME.md` line 1114
- **Issue**: "at the throttle cadence (≈ the cool-down, default 30m)" — the throttle cadence and cool-down are the same value (both 30m). The `≈` suggests they're close but not identical, which is misleading. They are the same config value.
- **Fix**: Change "≈ the cool-down" to "= the cool-down" or simply "the cool-down."

---

**LOW-3**: Known deferred noted — `/work/assign` endpoint fiction (#12495)

- **Location**: `docs/AGENT-RUNTIME.md` §8.3 lines 924, 948, 1005–1010 (multiple references to `POST /work/assign`)
- **Issue**: Per the audit task's KNOWN/DEFERRED note: "§8.3 still references the `/work/assign` endpoint, a documented fiction tracked in #12495 (full reconciliation deferred)." The §8.3 backstop subsection should be aware of this — if it references `/work/assign` as a mechanism, it should note the fiction. If the backstop describes the sentinel injecting an `assigned-to` event directly (per `sentinel-halt-body.md` line 12: "inject an `assigned-to` wake event"), it should specify the actual mechanism (EAD-emitted, not `/work/assign`). This is noted once per instruction — not over-flagged.

---

### Cross-Reference Consistency (explicitly verified)

The following cross-reference pairs were audited and found **consistent**:

| Reference A | Reference B | Verdict |
|---|---|---|
| §8.6.1 "two orthogonal wake sources" (line 1115) | §8.0 Monitor/event_poll (lines 749–773) + §8.1 loop structure | **Consistent** — Monitor = forge events, driver = timer idle-check; both feed the same §8.1 loop entry |
| §8.6.1 "no harness change" (line 1121) | HARNESS-ARCH §7.2 (harness spawn steps) | **Consistent** — cron scheduling is Claude Code runtime-side, no harness endpoint needed |
| §8.6.1 driver "LAZY (armed on first idle, not boot)" (line 1122) | §8.2 boot sequence (lines 870–873) | **Consistent** — boot steps do not include driver scheduling; §8.2 step 4 enters §8.1 loop which reaches idle naturally |
| §8.6.1 driver "BOUNDED (scan-counter cancels cron)" (line 1123) | §8.6 throttle (line 1100) + flowchart (lines 1073–1098) | **Consistent** — flowchart shows `Cap` node with `scan_count ≥ Idle Scan Burst?` → `Cancel` |
| §8.6.1 "re-arms on re-entering idle after forge work" (line 1123) | §8.6 flowchart `Idle → NUDGE → Start → Process → Start → … → QEmpty → Arm` | **Consistent** — the `Arm` node runs on every entry to the drained branch, re-arming |
| §8.3 backstop "pipeline sentinel is a PM responsibility" (described) | §8.6 line 1103 (pm subloop = "pipeline sentinel + improvement scan") | **Consistent** — PM owns the sentinel in both |
| §8.3 backstop "EAD polls forge state, not comment bodies" (described) | §5.4 EAD rules (lines 425–438) | **Consistent** — EAD maps status labels, human-comment authorship, and PR state; does not parse comment body semantics |
| §8.3 backstop "comment-only handoffs ride no event" (described) | `comment-handling.md` lines 8–10 ("Comments are NOT standalone event triggers. A bare comment on an issue does NOT wake any agent.") | **Consistent** — the backstop is the *response* to the documented limitation |
| §8.6.1 driver vs HARNESS-ARCH §15 liveness | §15.1 lines 550–561 (activity heartbeat + pause-aware guard) | **Complementary**, not conflicting — driver generates tool calls during idle which produce §15 heartbeats; driver cancellation after burst → idle agent with no dispatched work → not actively monitored per §15.1 |
| §8.6.1 vs event-mode-contract.md boot (Case A) | `event-mode-contract.md` lines 14–39 | **Consistent** — contract boot steps do not mention driver scheduling; driver is lazy (first idle, not boot), so no boot-step entry is needed |

## Vault Candidates
- **Type**: learning — "Periodic self-wake is required for event-mode idle-work scheduling because event_poll only fires on forge events" — **Why**: This is the architectural insight behind #12506 and §8.6.1; generalizes to any event-driven system where the wake mechanism is purely event-triggered — idle-work (maintenance, improvement scans) needs a separate timer-based re-entry path.
- **Type**: pattern — "Bounded-burst idle driver: lazy arm, scan-counter, cancel-at-threshold, re-arm on fresh activity" — **Why**: Reusable pattern for any agent that needs to do periodic maintenance during idle but must not loop forever — the three-phase lifecycle (arm-on-first-idle → count-up → cancel-at-threshold → re-arm-on-activity) is clean and could apply to other maintenance loops.
- **Type**: learning — "Arch-doc changes that declare sub-skill edits as 'part of the implementation' create a merge-time inconsistency window if the sub-skill edit is not bundled in the same PR" — **Why**: §8.6.1 line 1125 declares the `idle-cooldown-loop.md` edit as implementation; WARNING-2 documents the gap. This is a process learning: arch-docs should either bundle companion sub-skill edits or use a tracking issue reference rather than declaring the edit as done.
```