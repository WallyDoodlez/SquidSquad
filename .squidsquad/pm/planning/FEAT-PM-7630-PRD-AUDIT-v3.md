Now I have all the data needed to produce the full audit. Let me compile the findings.

---

# FEAT-PM-7630-PRD-AUDIT-v3 Research — Full PRD v2 Audit

## Summary

I performed a full audit of the PRD v2 at `.squidsquad/pm/planning/FEAT-PM-7630-PRD.md` (860+ lines), cross-referencing it against the locked decisions in `.squidsquad/pm/planning/FEAT-PM-7630-CONTEXT.md`, the L1-L4 architecture definition at `references/roles/LAYERS.md`, the actual codebase (harness.py, event_bus.py, event_catalog.py, all 4 roles' includes.yml and instructions.md), and the vault decisions/patterns. I verified all referenced file paths, line numbers, and existing infrastructure claims.

The PRD v2 represents a substantial architectural simplification from the earlier RESEARCH.md and GAP-REVIEW.md — collapsing from 30+ event types to 5, replacing the complex `POST /events/{id}/complete` closure API with simple ack events, and eliminating L2/L3 event-reaction sub-skills. These simplifications are directionally correct. However, the PRD v2 **silently overrides 5 out of 13 locked decisions in CONTEXT.md** without flagging the overrides or providing rationale. It contains 2 internal inconsistencies, 1 config gate that contradicts the locked "kill cycles entirely" decision, and 4 missing details that would stall implementers.

**Primary risk**: The human signed off on CONTEXT.md as "Locked Decisions (human decided)." If the PRD v2 ships without reconciling these contradictions, the implementation team will be blocked on which version of reality to build.

## Vault Context

- **BRIEFING.md priorities**: #7630 explicitly listed as active priority; supersedes #6056, #5775, #5613. "All mechanical cycle steps move to harness." "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose."
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 mechanical/creative split is the foundation #7630 builds on. [[decision-pid-primary-liveness]] — PID is primary, .health is informational. Relevant because PRD replaces PID polling with ack-based health. [[decision-self-healing-sentinel]] — two-tier self-healing (immediate unstick + root-cause bug filing) applies to ack timeouts. [[decision-watchdog-supervisor]] — centralizes lifecycle management; harness in event-driven mode subsumes watchdog role.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — the core pattern driving #7630. Any event reaction with >2 conditional branches should be a script.
- **Human preferences**: "any kind of cyclic work needs to be programmed deterministically" — supports event-driven. "just use PID, it's more direct" — partially conflicts with ack-based health (PID check is still in the diagnosis path but demoted from primary to fallback).
- **Related learnings**: [[learning-atomic-migration-strategy]] — templates, scripts, and harness changes must deploy atomically.

## Findings

### FINDING 1 [CRITICAL]: Closure mechanism contradiction — PRD overrides Locked Decisions #4, #12, #13

**CONTEXT.md Locked Decision #4** (line 34-37):
> "When the agent finishes processing an event, it MUST call `POST /events/{event_id}/complete` with a structured result payload (status transitions, tracker comments, commit message, summary). The harness processes the result (executes transitions, commits, pushes) and marks the event closed."

**CONTEXT.md Locked Decision #13** (lines 71-78):
> "Closure is two-phase to survive crashes mid-handling: 1. Agent POSTs `/events/{id}/complete` with payload 2. Harness persists `state=received` + payload with `fsync` 3. Harness executes side effects 4. Harness persists `state=closed` with `fsync`"

**CONTEXT.md Locked Decision #12** (lines 65-69):
> "Idempotency markers: tracker comments include `<!-- event_id:abc123 -->`, commit trailers include `Event-Id: abc123`, API result cache keys by event_id"

**PRD v2** (lines 303, 399-400, 529, 613-618):
> "Agent emits `ack {event_id}` via POST /events after handling any event"
> "The `POST /events/{id}/complete` endpoint from earlier PRD drafts is removed."
> "event_bus.py: Add `ack(event_id, role)` function (~20 lines): POST ack event to `/events`. Fire-and-forget like `emit()`."
> "After completing your work, ack the event: `python references/scripts/event_bus.py ack <event_id> [ROLE]`"

**Severity**: **CRITICAL**. The PRD replaces a structured, two-phase, fsync-durable closure API containing side-effect execution, crash recovery, and idempotency markers with a fire-and-forget ack. This is a fundamental architectural change. Locked Decisions #4, #12, and #13 are all invalidated. The PRD does not acknowledge this as an override, does not explain the rationale, and does not reconcile the 12-13 lost capabilities (side-effect execution, idempotency, crash recovery replay of `received`-state events).

**Recommended fix**: Either (a) add an explicit "Locked Decision Override" section to the PRD documenting that #4, #12, #13 are replaced by the simpler ack model with rationale, OR (b) reinstate the two-phase closure API if the human wants side-effect execution in harness. The simpler ack model may be correct — the agent commits/pushes its own work, and the harness just tracks lifecycle — but this needs explicit sign-off.

---

### FINDING 2 [CRITICAL]: scan-due removed — PRD overrides Locked Decision #5

**CONTEXT.md Locked Decision #5** (lines 39-40):
> "Harness tracks `last_event_completed[role]` timestamp per role. After 10 minutes with no completed events, harness emits a `scan-due` event. PM wakes, runs improvement scan, closes the event with findings."

**PRD v2** (lines 259, 297-303, 325):
> Scan trigger is NOT in the 5-event model. Instead: "Agent self-initiates per cooldown (15 min, scan immediately on idle)."
> "scan-cooldown: 15 minutes between scans (scan immediately on idle, then cooldown)"

**Severity**: **CRITICAL**. The PRD reverts scan triggering from harness-enforced (deterministic, a key #7630 goal) back to agent-self-initiated (the exact pattern #7630 was created to eliminate). The BRIEFING.md says "all mechanical cycle steps move to harness." Moving scan triggering back to agent prose contradicts the entire EPIC's premise. The GAP-REVIEW.md already identified this tension (line 231): "Idle timeout = time-based polling, not event-driven."

**Recommended fix**: Add `scan-due` as a 6th event type, OR explain explicitly that the 15-min agent-self-initiated scan is an acceptable regression from the deterministic model, OR make the harness emit `assigned-to` to PM when the scan cooldown elapses with no active work.

---

### FINDING 3 [CRITICAL]: Re-emit vs no-reemit — PRD overrides Locked Decision #11

**CONTEXT.md Locked Decision #11** (lines 45-46):
> "Events are single-shot. If an event is not closed within its hard timeout, the harness marks it terminal (`timed-out`), advances the cursor, and never reemits."

**PRD v2** (lines 68, 230-244, 361-368):
> "Harness re-emits the event (retry_count: 1)" 
> "Ack timeout → re-emit → max retries → declare dead + reboot → re-emit to rebooted agent"

**Severity**: **CRITICAL**. The PRD's entire health and recovery model depends on re-emitting events on ack timeout. CONTEXT.md explicitly says events never reemit. These are diametrically opposed. The CONTEXT.md model uses per-event-class timeouts with a diagnosis matrix to determine agent action (respawn, restart, alert human) but never reemits the event. The PRD model reemits the event up to N times. The reemit approach is simpler and more self-healing (aligns with [[decision-self-healing-sentinel]]), but it's a direct override of Locked Decision #11.

**Recommended fix**: Flag Locked Decision #11 as overridden. Explain that the ack-timeout + reemit model is intentionally different: it's simpler (no per-event-class timeout matrix), more self-healing (retry before escalate), and integrates health monitoring and event delivery into one mechanism.

---

### FINDING 4 [HIGH]: L2 event-reactions contradiction — PRD says none needed, CONTEXT.md Section 7 requires them

**CONTEXT.md Section 7** (lines 130-135):
> "Event reactions follow L1-L4 layered structure: L1 universal `common/event-reactions.md`, L2 role-specific `roles/{role}/event-reactions.md`, L3 behavioral adaptation via config, L4 human overrides"

**PRD v2** (lines 310-311, 649-652):
> "No L2/L3 event-reaction sub-skills needed."
> "The simplified 5-event model eliminates the need for per-role event-reaction files."
> "Roles already know how to handle issues from their existing role instructions."

**Severity**: **HIGH**. Section 7 of CONTEXT.md is not a "Locked Decision" — it's under "Dev Discretion" area of CONTEXT.md. However, it represents significant prior planning (the entire `FEAT-PM-7630-L1L4-REACTIONS.md` research was dedicated to this). The PRD's position is defensible (5 events don't need per-role variation at the event-protocol level), but the PRD should explicitly state this is an intentional scope reduction and why it's safe.

**Recommended fix**: Add a note: "L2/L3 event-reaction sub-skills from CONTEXT.md Section 7 are intentionally omitted. Rationale: with only 5 L1-universal events, role-specific behavior is already encoded in each role's `instructions.md` and existing sub-skills. Adding per-role event-reaction files would duplicate existing role guidance."

---

### FINDING 5 [HIGH]: Includes.yml change is contradictory/confusing about event-reactions

**PRD v2** (lines 668-670):
> "REMOVE: `common/event-reactions` (old flat file)"
> "ADD: `common/event-driven-workflow` (L1 — how to watch inbox via Monitor, process events, ack)"
> "No new L2 event-reaction includes needed"

But PRD also says (lines 638-649):
> "Rewritten sub-skill: `common/event-reactions.md` — rewritten to describe the 5-event model (~30 lines)."

**Severity**: **HIGH**. The includes.yml changes say to REMOVE `common/event-reactions` but the PRD also says event-reactions.md is *rewritten* and kept. The actual includes.yml change removes event-reactions and adds event-driven-workflow — these are DIFFERENT files. So event-reactions.md exists as a file in the repo but is NOT included in any agent's manifest after migration. Is that intentional? Or should the rewritten event-reactions.md also be included? The PRD is ambiguous.

**Current includes.yml state** (verified from all 4 files):
- All 4 roles currently include `common/event-reactions` (e.g., `references/roles/pm/includes.yml` line 5)

**Recommended fix**: Clarify: "`common/event-reactions.md` is rewritten as reference documentation for the 5-event model but is NOT included in agent manifests — it serves as authoritative reference for event types. Agent-facing event guidance comes from `common/event-driven-workflow.md` only."

---

### FINDING 6 [MEDIUM]: Config gate contradicts "kill cycles entirely" — backward compat path adds complexity

**PRD v2** (lines 82-84, 112, 757-761):
> `event-driven: yes|no` config gate, default "no" during development
> "Retained in codebase for `event-driven: no` backward compat"
> "Agents self-loop via `/loop`" when event-driven is "no"

**CONTEXT.md Locked Decision #3** (lines 29-32):
> "Kill cycles entirely — pure event-driven. No /loop, no cycle_pre.py, no cycle_post.py, no cycle-input.json, no cycle-output.json, no cycle counters."

**Severity**: **MEDIUM**. The config gate contradicts the spirit of "kill cycles entirely." Maintaining dual-mode compose, dual-mode sub-skill includes, and retaining cycle_pre.py/cycle_post.py "for backward compat" creates a permanent fork in the architecture. The PRD says backward compat is for "one version" (line 112) but Phase 4 (lines 819-835) explicitly defers removal. The risk is that the config gate becomes the permanent state and cycles are never truly killed.

However, the config gate is a pragmatic rollout strategy — supported by the vault's [[learning-atomic-migration-strategy]]. The contradiction is philosophical, not implementation-blocking.

**Recommended fix**: Add an explicit sunset clause: "The `event-driven: no` backward compat path will be removed in the version after #7630 ships (Phase 4). The config gate is a rollout safety mechanism, not a permanent dual-mode."

---

### FINDING 7 [MEDIUM]: Internal inconsistency — Stop Grace Period mentioned but not in config template

**PRD v2 line 659** (L4 overrides):
> "Stop Grace Period: seconds before forced kill on stop-requested"

**PRD v2 lines 689-699** (config.md template):
> No `Stop Grace Period` field listed.

**PRD v2 lines 700-710** (FIELD_MAP):
> No `stop-grace-period` mapping.

**Severity**: **MEDIUM**. The "Stop Grace Period" override is described in prose but never makes it into the config schema. An implementer wouldn't know whether to include it or not.

**Recommended fix**: Either add `Stop Grace Period` to the config.md template and FIELD_MAP, or remove it from the L4 overrides section (it's not in the 5-event model's critical path — the agent simply finishes its current event and acks the stop-requested).

---

### FINDING 8 [MEDIUM]: cycle.py retained contradicts "kill cycles entirely"

**PRD v2** (line 563):
> "No changes. Still used for timestamps, status-bar, iteration-logs."

**CONTEXT.md Locked Decision #3** (lines 29-30):
> "No /loop, no cycle_pre.py, no cycle_post.py, no cycle-input.json, no cycle-output.json, no cycle counters, no iteration logs in the current format."

**Severity**: **MEDIUM**. The PRD says iteration logs are kept (renamed to per-wake logs), and `cycle.py` is kept for timestamps and iteration-logs. This is a pragmatic compromise — the utilities are useful even if the "cycle" concept is gone. But `cycle.py` still has "cycle" in its name and the iteration logs still have a sequential counter (Q4, line 856). An implementer reading "kill cycles entirely" then seeing "cycle.py — no changes" will be confused.

**Recommended fix**: Clarify: "`cycle.py` is retained as a utility module for timestamps and structured logging. The sequential counter remains but is renamed from 'cycle number' to 'wake number' or 'event sequence.' The file may be renamed post-Phase-4."

---

### FINDING 9 [MEDIUM]: event-sensitivity default contradicts atomicity rule

**PRD v2** (line 88, 323-326):
> `event-sensitivity: 5` — "events behind queue tip (debounce buffer — agents process settled events, not bleeding edge)"
> `events-atomic: true` — "events are never interrupted mid-handling"

**Severity**: **MEDIUM**. The concept of "5 events behind queue tip" as a debounce buffer is hard to reconcile with the atomicity rule. If events are atomic and the agent processes one event at a time, what does "5 behind" mean in practice? The agent processes event 1, then event 2 comes, etc. There's no debouncing to do for sequential processing. The sensitivity concept only makes sense if events can be superseded/coalesced (e.g., two `assigned-to` for the same issue merge into one), but the PRD doesn't describe coalescing behavior.

**Recommended fix**: Either remove `event-sensitivity` as a concept (atomic sequential processing makes it unnecessary), or document how events are coalesced/superseded so that "N behind tip" has meaning.

---

### FINDING 10 [LOW]: Missing detail — working-state updates not in event-driven-workflow.md

**PRD v2 lines 578-636** (event-driven-workflow.md template):
> The template covers startup, event processing, acking, and what agents do NOT do. It does NOT mention:
> - Writing `.squidsquad/[ROLE]/working-state.md` after completing work
> - Checkpointing working state on `stop-requested` (line 608 mentions it for stop-requested only)

**Severity**: **LOW**. The PRD Section 5.2 says "Working state update → agent writes directly; harness commits" (line 522-523), but the agent template never tells the agent WHEN to write working state. Currently cycle-runner.md covers this.

**Recommended fix**: Add to event-driven-workflow.md: "After processing any event, update your working state: write `.squidsquad/[ROLE]/working-state.md` with your current task, findings, and next steps. The harness will commit and push it after processing your ack."

---

### FINDING 11 [LOW]: Missing detail — existing EMITTED events fate unclear

**PRD v2** (lines 303, 315-317, 534):
> 5 agent-facing event types. Harness-internal events (not delivered to agents): git-pull, git-push, git-commit, branch-checkout, pr-create, compose-completed, status-transition, tracker-comment.
> "old event types that are now harness-internal only (`new-commits`, `new-issue`, `issue-updated`, `context-pressure`, `pr-conflict`, etc.) are not delivered to agents — they remain in EMITTED for harness observability"

**Current event_catalog.py** (lines 26-87, verified): EMITTED has 12 types: cycle-start, cycle-end, git-pull, git-push, git-commit, status-transition, tracker-comment, branch-checkout, pr-create, pr-merge, pr-merged, compose-completed. RECOGNIZED has 5: verification-failed, verification-passed, agent-health, phase-change, request-merge.

**Severity**: **LOW**. The PRD says cycle-start/cycle-end "go away" but doesn't address whether they're removed from EMITTED or moved to RECOGNIZED. The catalog clean-up plan is underspecified. An implementer would need to decide: remove from catalog entirely, move to RECOGNIZED, or leave in EMITTED but stop emitting. The PRD mentions keeping them "in EMITTED for harness observability" — but `cycle-start` and `cycle-end` no longer happen in event-driven mode.

**Recommended fix**: Add a catalog migration table: for each of the 17 current event types, specify: removed from catalog / moved to harness-internal only / unchanged / renamed.

---

### FINDING 12 [LOW]: No mention of `references/roles/instructions.md` (L1 base) changes

**PRD v2** (lines 672-683, 101): 
> "Role instructions.md changes (all 4 roles)" — detailed. 
> "Role SOUL.md files" — mentioned.
> No mention of `references/roles/instructions.md` (L1 base agent definition)

**Current L1 instructions.md** (verified at `references/roles/instructions.md`, line 7):
> "You work autonomously in cycles following the Ralph Loop."
> "Follow the Ralph Loop — each cycle is a complete unit of work."

**Severity**: **LOW**. The L1 base instructions.md contains Ralph Loop references that must also be updated. The PRD covers all 4 role-specific instructions.md and SOUL.md files but omits the L1 base file that gets prepended to every agent's CLAUDE.md. LAYERS.md (lines 41-44) confirms: "instructions.md → CLAUDE.md: L1 + L2 + L3 assembled."

**Recommended fix**: Add `references/roles/instructions.md` to the template changes section. Replace "Follow the Ralph Loop" with "React to events dispatched by the harness" and "each cycle is a complete unit of work" with "each event is a complete unit of work."

---

## Internal Consistency Summary

| Section | 5-event model? | Ack closure? | No L2/L3 sub-skills? | Consistent? |
|---------|---------------|-------------|---------------------|-------------|
| Summary (§1) | ✅ 5 events | ✅ Ack | ✅ | ✅ |
| Architecture (§2) | ✅ | ✅ Ack timeout model | Implicit | ✅ |
| Event Design (§3) | ✅ 5 types (lines 297-303) | ✅ "Every event gets an ack" (line 308) | ✅ "No L2/L3" (line 311) | ✅ |
| Includes.yml (§5.3) | ✅ | ✅ | ⚠️ Confusing removal of event-reactions (Finding 5) | ⚠️ |
| Role instructions (§5.3) | ✅ | ✅ | ✅ | ✅ |
| Config changes (§5.4) | ⚠️ Missing Stop Grace Period (Finding 7) | ✅ | ✅ | ⚠️ |
| Phasing (§6) | ✅ | ✅ | ✅ | ✅ |
| Overall consensus | ✅ | ✅ | ✅ | Minor internal issues only |

The PRD is internally consistent on the big three: 5-event model, ack closure, no L2/L3 sub-skills. All sections agree. The inconsistencies are in the finer details (config field missing, includes.yml ambiguity, L1 base file omission).

---

## Architectural Alignment with LAYERS.md

| LAYERS.md concept | PRD v2 treatment | Alignment? |
|-------------------|-----------------|------------|
| L1: Universal agent definition | event-driven-workflow.md is L1 sub-skill, event-reactions.md rewritten as L1 reference | ✅ |
| L2: Role-specific | L2 role instructions.md updated, existing role sub-skills retained | ✅ |
| L3: Domain variant | No L3 event-reaction sub-skills needed (PRD line 652). Domain variants inherit L2 behavior naturally | ✅ aligns with LAYERS.md vertical scaling |
| L4: Project overrides | config.md Event Driven section with overridable defaults | ✅ |
| SOUL.md personality | "Remove Ralph Loop references" (PRD line 683). SOUL.md is personality only — aligns with LAYERS.md line 42 | ✅ |
| compose.py assembly | compose.py deploy-all regenerates CLAUDE.md + SOUL.md (PRD line 107) | ✅ |

The PRD aligns cleanly with LAYERS.md. The removal of L2/L3 event-reaction sub-skills is a scope simplification that doesn't violate the layered architecture — it just means the 5-event model is simple enough that L1 universal guidance suffices for all roles.

---

## Remaining References to Old Model Artifacts

1. **PRD architecture diagrams** (lines 118-166) — correctly labeled "Current Architecture (Cycle-Based)" and used for comparison. Clean.
2. **PRD line 563** — "cycle.py — No changes." Name is legacy, but the note acknowledges this. Minor.
3. **PRD line 856** — Q4: "Do we keep cycle_number for iteration logs, or switch to event_id-based logging?" References "cycle" concept but proposes event_id replacement. Clean transition.
4. **All 4 role instructions.md** (verified at `references/roles/pm/instructions.md` lines 5, 13-18, 39-50; `dev/instructions.md` lines 5, 23-28, 33-49; `qa/instructions.md` lines 5, 29-37, 42-49; `dm/instructions.md` lines 5, 31-37, 42-49) — all contain "Ralph Loop," `/loop`, and "cycle" references. The PRD correctly identifies these for removal.
5. **L1 base instructions.md** (`references/roles/instructions.md` line 7) — contains "Follow the Ralph Loop" and "each cycle is a complete unit of work." NOT mentioned in PRD for changes (Finding 12).
6. **All 4 includes.yml** (verified) — all include `common/cycle-runner`, `common/event-reactions`, `common/context-pressure`, `common/self-restart`. PRD correctly identifies these for removal (lines 568-574).

---

## Recommendation

**Feasible with caveats — needs CONTEXT.md reconciliation before implementation.**

The PRD v2 is a significant improvement over the earlier RESEARCH.md and GAP-REVIEW.md: 5 events instead of 30+, simple ack instead of two-phase closure API, no L2/L3 sub-skill proliferation. The internal structure is consistent. The LAYERS.md alignment is clean.

However, the PRD cannot proceed to implementation until the CONTEXT.md contradictions are resolved. The implementer would face five conflicting "locked decisions" with no guidance on which to follow. The three critical findings (F1, F2, F3) must be resolved with the human before any code is written.

**If the human confirms the PRD v2 direction**: The PRD should add a "Locked Decision Overrides" section explicitly listing each overridden decision with rationale. This gives the implementer unambiguous authority to proceed.

**If the human wants to preserve CONTEXT.md locked decisions**: The PRD needs substantial revision to reinstate `POST /events/{id}/complete` closure, `scan-due` as a 6th event type, and the no-reemit model.

## Vault Candidates

- **Type**: decision — **Ack-based health monitoring replaces PID polling** — **Why**: The PRD v2 proposes replacing PID-based health polling with ack timeout detection. This is a novel architectural evolution from [[decision-pid-primary-liveness]] worth capturing. Harness sends event → no ack → retry → kill/reboot. PID check remains as a secondary verification before killing.
- **Type**: decision — **5-event universal model vs 30+ typed events** — **Why**: The PRD v2's key architectural simplification — collapsing from 30+ L1-L4 event types to exactly 5 L1-universal events — is a significant design decision. Rationale: the forge (GitHub Issues/PRs) already contains all work context, events are routing signals only. This contradicts the CONTEXT.md model and the prior L1L4-REACTIONS research. Capturing this reversal is important for future architectural reasoning.
- **Type**: learning — **Config gating for phased migration has hidden costs** — **Why**: The PRD v2's `event-driven: yes/no` gate adds substantial complexity (dual-mode compose, retained cycle_pre/cycle_post, conditional sub-skill includes). While it enables safe rollout, the experience of maintaining two architectures simultaneously should be documented. If the gate becomes permanent, the architecture accumulates technical debt.
- **Type**: learning — **Locked decisions can become stale within the same EPIC's lifecycle** — **Why**: The CONTEXT.md was written as "Locked Decisions (human decided)" but the PRD v2 (written afterward as the authoritative implementation spec) overrides 5 of 13 locked decisions. This demonstrates that locked decisions at the CONTEXT.md stage can become obsolete as the PRD matures. The process gap is that CONTEXT.md was not updated when the PRD v2 took a different direction. A vault note on this pattern could improve future EPIC workflows.
- **Type**: pattern — **Forge as source of truth — events as routing signals only** — **Why**: The PRD v2's design principle (line 306) that "the forge is the source of truth" and "events are routing signals, not context carriers" is a reusable architectural pattern. By keeping event payloads minimal ({role, issue_or_pr}) and having agents read the full context from GitHub, the event system stays simple and avoids event-context synchronization problems. This could apply to any event-driven system that has an external source of truth.