Now I have all the data I need. Let me compile the comprehensive audit. I have the updated PRD content from my initial read (847 lines), the old branch version, the PRD-AUDIT from a prior audit, and the actual codebase state. Let me produce the final document:

---

# FEAT-PM-7630-PRD-CONSISTENCY Research — Internal Consistency Audit of 5-Event Model Update

## Summary

The PRD (`FEAT-PM-7630-PRD.md`) was updated — Sections 3.2 and 3.3 now describe a clean 5-event model (assigned-to, stop-requested, shipped, version-bump, ack), all at L1 universal, with `ack` replacing the old `POST /events/{id}/complete` endpoint. However, this update was a **surgical patch** — only Sections 3.2 and 3.3 were rewritten. **22 other sections** across the document still reference the old 30+ event model, the old endpoint, L2/L3 event-reaction sub-skills, 14 agent-delivered events, and 18 mechanical events. The PRD is internally contradictory — an implementer reading beyond Section 3.3 would implement the old architecture.

The core contradiction: Section 3.2 says "No L2/L3 event-reaction sub-skills needed" and "ack replaces POST /events/{id}/complete," but Section 5.1 still specifies implementing `POST /events/{id}/complete` with a closure payload of `{role, summary, status_transitions, tracker_comments}`, Section 5.3 still shows `event_bus.py close` with `--transitions` and `--comments` flags, and Phase 2 deliverables list the old endpoint as a requirement.

**Recommendation**: Needs rethinking — not of the 5-event model itself (which is sound), but of the PRD document consistency. Every section after 3.3 needs a pass to align with the 5-event model. The document cannot be merged or implemented in current state without causing confusion or misimplementation.

## Vault Context

- **BRIEFING.md priorities**: #7630 EPIC is active priority — "all mechanical cycle steps move to harness." The 5-event model aligns with this.
- **Related decisions**: [[decision-cycle-runner-architecture]] — references #7630 as successor; cycle_pre/post elimination is correct direction.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose." The 5-event model supports this.
- **Human preferences**: "any kind of cyclic work needs to be programmed deterministically" and "agents should react to events, not run multi-step cycles." The 5-event model aligns perfectly. "Prefers direct/mechanical checks over indirect state files" — context pressure threshold 70%.
- **Related learnings**: [[decision-self-healing-sentinel]] — two-tier self-healing applies to event timeout handling (still valid in 5-event model).

## Impact Analysis

- **Files touched by this audit**: `FEAT-PM-7630-PRD.md` (the PRD itself) — 22 of ~28 sections need revision.
- **Behavior changes**: None — this is a document consistency fix, not a code change.
- **Dependencies**: The prior audit (`FEAT-PM-7630-PRD-AUDIT.md`) found L3/L4 labeling errors which have been fixed. This audit finds the remaining old-model artifacts.

## Findings

### CATEGORY 1: References to Removed/Old Events (agent-deliverable events no longer in the 5-event model)

---

**F1 — Edge Cases uses old event type `pr-merged`** (PRD line 69)

> "A single event (e.g., **pr-merged**) may need to wake pm (to transition issues) AND skill (to pull latest)."

**Inconsistency**: `pr-merged` is an old event type from the 30+ event model. Under the 5-event model, this scenario would be an `assigned-to` or `shipped` event. **Fix**: Replace "pr-merged" with "assigned-to" or "shipped." Rewrite as: "A single event (e.g., `shipped` from DM) wakes all agents."

---

**F2 — Integration Risks references `pr-merged` event** (PRD line 74)

> "harness merge emits **pr-merged**, which wakes PM+QA."

**Inconsistency**: Same old event type. **Fix**: Replace with: "harness processes merge → DM may emit `shipped` event → wakes all agents."

---

**F3 — Section 2.3 comparison table: "scan event" delivered to agents** (PRD line 257)

> "Scanning | Harness detects 'no events for N cycles' → emits **scan event** → agent scans"

**Inconsistency**: The 5-event model has no `scan` event delivered to agents. Scans are behavioral tuning (Section 3.2 line 316: `scan-cooldown: 15 minutes`). **Fix**: Replace with: "Agent self-initiates scans per behavioral tuning cooldown (default 15 min). No scan event from harness."

---

**F4 — Section 2.3: "stop-event" instead of "stop-requested"** (PRD line 258)

> "Stopping | Harness sends **stop-event**, agent exits on next wake boundary"

**Inconsistency**: The 5-event model uses `stop-requested`. "stop-event" is ambiguous and could imply a separate event. **Fix**: Replace with "`stop-requested` event."

---

**F5 — Section 2.3: Old restart mechanism** (PRD line 259)

> "Restarting | **cycle_post.py exit 42 on context pressure**"

**Inconsistency**: Under the new model, harness health-watcher monitors context pressure and proactively kills/respawns. cycle_post.py no longer handles restart. **Fix**: Replace with "Harness monitors context-pressure file, proactively kills/respawns."

---

**F6 — Section 2.3: Old status transition closure pattern** (PRD line 256)

> "Status transitions | Agent writes **cycle-output.json**; harness executes transitions on event closure"

**Inconsistency**: Under the 5-event model, agents handle status transitions as part of their creative work and just emit `ack`. No closure payload with transitions. **Fix**: Replace with "Agent executes transitions during creative work; harness commits. No closure payload needed."

---

**F7 — Section 4.3 harness state example uses old event type** (PRD line 412)

```json
"event_type": "pr-merged",
```

**Inconsistency**: Example JSON uses old event type. **Fix**: Change to `"assigned-to"` or `"shipped"`.

---

**F8 — Section 5.2 tracker.py references old agent-deliverable events** (PRD lines 541-542)

> "Already emits **status-transition** and **tracker-comment** events. These events are consumed by harness monitors to detect work..."

**Inconsistency**: Under the old model, `status-transition` and `tracker-comment` were delivered to agents (see old Section 3.3 event-reaction matrix). Under the 5-event model, these are harness-internal only — monitors use them to decide when to emit `assigned-to` events. The PRD should clarify they are NOT delivered to agents. **Fix**: Add "(harness-internal only; not delivered to agents. Monitors translate these into `assigned-to` events when agent action is needed.)"

---

**F9 — Section 5.2 cycle_post absorption: `version-bump-due` event** (PRD line 511)

> "Version bump (DM) → harness executes on **version-bump-due** event"

**Inconsistency**: The 5-event model has `version-bump` (DM-emitted), not `version-bump-due` (harness-emitted). **Fix**: Replace with "DM emits `version-bump` event → harness processes it."

---

**F10 — Section 5.1 monitors emit old agent-deliverable events** (PRD lines 457, 459, 461)

> "emits **new-commits** event when new commits detected"
> "emits **new-issue** and **issue-updated** events"
> "emit **context-pressure** event when threshold exceeded"

**Inconsistency**: These are described as if delivered to agents. Under the 5-event model, monitors still run but their outputs are harness-internal signals. The harness translates monitor findings into the 5 agent-facing events as appropriate (e.g., a new issue → harness emits `assigned-to` for PM). **Fix**: Add "(harness-internal only)" qualifier to each, or clarify how they translate into 5-event-model events.

---

**F11 — Section 5.2 event_catalog.py additions include old event types** (PRD lines 517-518)

> "Add to RECOGNIZED: **new-commits**, **new-issue**, **issue-updated**, **context-pressure**, **pr-conflict**, **scan-needed**, **stop-request**, **restart-request**, **event-timeout**, **event-closed**, **agent-wake**, **agent-diagnose**"

**Inconsistency**: This list comes from the old 30+ event model. Several (`scan-needed`, `stop-request`, `restart-request`, `agent-wake`) are either removed or renamed in the 5-event model. **Fix**: Reclassify: harness-internal events go in a new INTERNAL tier; agent-facing events are only the 5 types (`assigned-to`, `stop-requested`, `shipped`, `version-bump`, `ack`). Remove `scan-needed`, rename `stop-request` → `stop-requested`.

---

**F12 — Phase 2 success criteria use old event names** (PRD lines 772-773)

> "Harness detects new commits on origin → emits **new-commits** event → wakes skill agent"
> "Harness detects new GitHub issue → emits **new-issue** event → wakes PM agent"

**Inconsistency**: These describe the old model where monitors emit directly to agents. Under the 5-event model: monitor detects change → harness translates → emits `assigned-to` targeting the appropriate role. **Fix**: Rewrite as: "Harness detects new commits on origin → emits `assigned-to {role: 'skill', issue_or_pr: ...}` → skill agent wakes."

---

### CATEGORY 2: References to Old POST /events/{id}/complete Endpoint (replaced by `ack` event)

---

**F13 — Section 2.2 Target Architecture diagram: old endpoint** (PRD line 199)

> `CLOSE_A["POST /events/{id}/complete<br/>(closure callback)"]`

**Inconsistency**: Should show `ack` event emission via `POST /events`. **Fix**: Replace with `ACK_A["emit ack {event_id}<br/>via POST /events"]`.

---

**F14 — Section 2.2 Event Flow diagram: old endpoint** (PRD line 224)

> `G["POST /events/{id}/complete"]`

**Inconsistency**: Same as F13. **Fix**: Replace with `G["emit ack {event_id}"]`.

---

**F15 — Section 3.1 Event Lifecycle Diagram: old endpoint** (PRD line 273)

> `IN_FLIGHT --> CLOSED: Agent calls POST /events/{id}/complete`

**Inconsistency**: Should be `ack` event. **Fix**: Replace with `IN_FLIGHT --> CLOSED: Agent emits ack {event_id}`.

---

**F16 — Section 3.1 note: old closure callback description** (PRD line 288)

> `note right of CLOSED: Harness processes closure callback\n(transitions, commits, logs)`

**Inconsistency**: Under the 5-event model, `ack` is just confirmation — the agent already did the work (transitions, commits). Harness just marks the event as handled. **Fix**: Replace with `note right of CLOSED: Harness marks event handled.\nAgent already did transitions/commits during creative work.`

---

**F17 — Section 5.1, item 1: POST /events/{id}/complete implementation** (PRD lines 441-445)

> "1. **POST /events/{id}/complete** (after line 889...):
> - Accept `{role, summary?, status_transitions?, tracker_comments?}`
> - Mark consumer as closed for this role
> - If all consumers closed, emit `event-closed` event, move to closed state
> - Return remaining consumers count or 'closed' status"

**Inconsistency**: This is the most severe contradiction. Section 4.2 line 375 correctly marks this endpoint as "REPLACED by ack event," but Section 5.1 still specifies full implementation. The closure payload (`status_transitions`, `tracker_comments`) is exactly the old pattern where the harness executes mechanical work from agent-provided data. Under the 5-event model: agent handles everything, emits `ack {event_id}` via `POST /events`. **Fix**: DELETE this section. Replace with: "1. **ack event handling in existing POST /events** — When `event_type: 'ack'` is received, harvest marks the referenced event as handled. If acking `stop-requested`: treat as shutdown confirmation."

---

**F18 — Section 5.2 event_bus.py: old close() function** (PRD lines 513-514)

> "Add: **close**(event_id, role, summary=None) function (~30 lines): POST to **/events/{id}/complete**. Fire-and-forget like emit()."

**Inconsistency**: Should just emit `ack` event. **Fix**: Replace with "Add: **ack**(event_id, role) function (~10 lines): Emits `ack {event_id, role}` via `POST /events`. Fire-and-forget."

---

**F19 — Section 5.2 event_bus_reader.py: old endpoint** (PRD line 520)

> "Add: **ack**(event_id, role) function (~15 lines): Calls POST **/events/{id}/complete**. Thin wrapper for agent use."

**Inconsistency**: Same. The function name is right (`ack`) but the implementation calls the wrong endpoint. **Fix**: "Calls `POST /events` with `event_type: 'ack', payload: {event_id}`."

---

**F20 — Section 5.3 event-driven-workflow.md: old close command** (PRD lines 591-601)

```bash
python references/scripts/event_bus.py close <event_id> [ROLE] \
  --summary "Brief description of work done" \
  --transitions '[{"number": 42, "from": "approved", "to": "in-progress"}]' \
  --comments '[{"number": 42, "message": "Picking up."}]' \
  --commit-message "role: description of changes"
```

**Inconsistency**: This shows the old closure model where agents pass status transitions and tracker comments through the API for harness execution. Under the 5-event model: agent does transitions/comments during creative work, then simply acknowledges. **Fix**: Replace with:
```bash
python references/scripts/event_bus.py ack <event_id> [ROLE]
```

---

**F21 — Section 5.1 EventLifecycleManager: close() not ack()** (PRD lines 467, 472)

> "`close(event_id, role)` — marks consumer closed"

**Inconsistency**: Method should be `ack(event_id, role)` to match the 5-event terminology. **Fix**: Rename `close()` → `ack()`.

---

**F22 — Section 5.1: "emit event-closed event"** (PRD line 448)

> "If all consumers closed, emit **event-closed** event, move to closed state"

**Inconsistency**: `event-closed` is an old harness-internal event. Under the 5-event model, `ack` IS the closure — when all registered agents have acked, the event is closed. No separate `event-closed` event needed. **Fix**: "If all registered agents have acked, mark event as closed in event_state."

---

**F23 — Phase 2 deliverables: old endpoint and functions** (PRD lines 762-770)

> "- **POST /events/{id}/complete** endpoint"
> "- EventLifecycleManager (dispatch, **close**, timeout)"
> "- cycle_post.py **closure call**"
> "- event_bus.py **close()** function"
> "- thin_launcher.py **--event flag + idle mode**"
> "- boot_remote.py **boot_agent_with_event()**"

**Inconsistency**: Multiple old-model deliverables. **Fix**: Replace with: "- ack event handling in POST /events", "- EventLifecycleManager (dispatch, ack, timeout)", "- event_bus.py ack() function". Remove "--event flag" and "boot_agent_with_event()" (not part of 5-event model).

---

**F24 — Phase 2 success criteria: old endpoint** (PRD line 774)

> "Agent processes event → calls **POST /events/{id}/complete** → event marked closed"

**Inconsistency**: Should be ack. **Fix**: "Agent processes event → emits `ack {event_id}` → harness marks event handled."

---

**F25 — Risk Register: old endpoint** (PRD line 821)

> "Idempotent closure: **POST /events/{id}/complete** is safe to call N times."

**Inconsistency**: Should reference ack. **Fix**: "Idempotent ack: emitting `ack {event_id}` multiple times is safe."

---

**F26 — Vault Candidates: old endpoint** (PRD line 843)

> "POST /events/{id}/complete is safe to call multiple times"

**Inconsistency**: Same. **Fix**: Replace with "ack event is idempotent."

---

### CATEGORY 3: References to L2/L3 Event-Reaction Sub-Skills (removed in 5-event model)

---

**F27 — Section 5.3 includes.yml: "14-event matrix" reference** (PRD line 651)

> "- REMOVE: `common/event-reactions` (old flat file with **14-event matrix**)"

**Inconsistency**: References the old "14 events" count from the previous model. While the instruction to remove the file is correct, the "14-event matrix" is a ghost of the old model. **Fix**: Replace with "old flat event-reactions file (pre-5-event model)."

---

**F28 — Section 5.3 event-reactions.md rewrite: "emit stopped"** (PRD line 628)

> "stop-requested reaction: finish current event atomically, checkpoint, stop Monitor, emit **stopped**"

**Inconsistency**: Under the 5-event model (Section 3.2 line 306): "An `ack` of `stop-requested` = agent stopped. No separate `stopped` event needed." Line 628 says "emit `stopped`" — contradicting the core design principle. **Fix**: Replace "emit `stopped`" with "emit `ack {event_id}`."

---

**F29 — Section 5.2 cycle_pre absorption: "Mechanical reactions"** (PRD line 501)

> "Mechanical reactions → harness processes inline on event receipt"

**Inconsistency**: This references the old L2 event-reaction sub-skill model where cycle_pre.py executed role-specific mechanical reactions for events. Under the 5-event model, there are no mechanical reactions — agents handle events per their existing role instructions. **Fix**: Remove this line or replace with: "Event routing → harness determines target agent(s) and dispatches."

---

**F30 — Section 5.3: "No L2 event-reaction sub-skills needed" is correct but surrounded by old-model text** (PRD line 634)

**Analysis**: Line 634 correctly states "No L2 event-reaction sub-skills needed." However, the preceding paragraph (lines 623-632) still describes writing `common/event-reactions.md` with per-event-type reactions — a holdover from when L2 sub-skills existed. The new 5-event model means `event-reactions.md` should only describe the universal protocol (5 events, all L1), not per-role event-specific guidance. **Fix**: The event-reactions.md content outline (lines 623-632) should be trimmed to only the universal ack protocol and atomicity rule, matching Section 3.2's 5-event table.

---

### CATEGORY 4: Sections That Contradict the 5-Event All-L1 Model

---

**F31 — Section 4.2 endpoint table: correctly marked "REPLACED" but still listed as new** (PRD line 375)

> `| POST | /events/{id}/complete | **REPLACED by ack event** ...`

**Inconsistency**: The table header says "New Endpoints Required" — listing a replaced endpoint as "new" is confusing. **Fix**: Either remove the row entirely and add a note, or move it to a "Removed/Replaced Endpoints" subsection.

---

**F32 — Section 3.2 behavioral tuning: "10 events behind queue tip"** (PRD line 315)

> "event-sensitivity: **10 events** behind queue tip (debounce buffer — agents process settled events, not bleeding edge)"

**Inconsistency**: With only 5 event types, a debounce buffer of 10 events doesn't make sense — there would rarely be 10 distinct events queued. **Fix**: Reduce default to 3, or re-conceptualize as seconds-behind rather than event count.

---

**F33 — Section 5.3 "Event Types and Responses" references old Section 3.3** (PRD line 624)

> "[Event-reaction matrix table — see Section 3.3 of PRD]"

**Inconsistency**: The old Section 3.3 was the 14-event reaction matrix. The new Section 3.3 is "Event Flow Examples" (4 examples with the 5-event model). The cross-reference is stale. **Fix**: Replace with "[See Section 3.2 for the 5-event types and agent reactions.]"

---

**F34 — Section 3.1 note: "Consumers determined by event type"** (PRD line 287)

> `note right of PENDING: Written to disk-persisted event-store\nConsumers determined by event type`

**Inconsistency**: The old model determined consumers by event type (e.g., `pr-merged` → pm+skill). Under the 5-event model, the emitter specifies the target (e.g., `assigned-to {role: "skill"}`). **Fix**: Replace with `Consumers specified by emitter in event payload`.

---

**F35 — Section 3.1 note: "Monitor tool detects file (sub-second)"** (PRD line 287)

> `note right of IN_FLIGHT: Timer starts for timeout\nMonitor tool detects file (sub-second)`

**Inconsistency**: The wake mechanism uses `event_poll.py` querying `GET /events` (HTTP), not file detection. "detects file" is a holdover. **Fix**: Replace "detects file" with "detects stdout from event_poll.py".

---

### Summary Table

| # | PRD Line(s) | Category | Old Reference | New Model Says | Severity |
|---|-------------|----------|---------------|----------------|----------|
| F1 | 69 | Old event | `pr-merged` | `assigned-to` or `shipped` | M |
| F2 | 74 | Old event | `pr-merged` | `shipped` | M |
| F3 | 257 | Old event | `scan event` | No scan event; behavioral tuning | M |
| F4 | 258 | Old event name | `stop-event` | `stop-requested` | L |
| F5 | 259 | Old mechanism | `cycle_post.py exit 42` | Harness proactive restart | M |
| F6 | 256 | Old pattern | `cycle-output.json` closure | `ack` only | M |
| F7 | 412 | Old event | `"pr-merged"` in JSON | `"assigned-to"` | L |
| F8 | 541-542 | Old events | `status-transition`, `tracker-comment` as delivered | Harness-internal only | M |
| F9 | 511 | Old event | `version-bump-due` | `version-bump` | M |
| F10 | 457,459,461 | Old events | `new-commits`, `new-issue`, `context-pressure` as agent events | Harness-internal only | H |
| F11 | 517-518 | Old events | 12 event types to add | Reclassify: internal vs. 5 agent-facing | H |
| F12 | 772-773 | Old events | `new-commits`/`new-issue` in success criteria | `assigned-to` event | M |
| F13 | 199 | Old endpoint | Diagram: `POST /events/{id}/complete` | `ack` via `POST /events` | M |
| F14 | 224 | Old endpoint | Flow diagram: old endpoint | `ack` event | M |
| F15 | 273 | Old endpoint | Lifecycle diagram: old endpoint | `ack` event | M |
| F16 | 288 | Old pattern | "closure callback (transitions, commits)" | Harness marks handled | M |
| F17 | 441-445 | Old endpoint | Full implementation of `POST /events/{id}/complete` | Already REPLACED per 4.2 | **H** |
| F18 | 513-514 | Old endpoint | `event_bus.py close()` → old endpoint | `event_bus.py ack()` → `POST /events` | H |
| F19 | 520 | Old endpoint | `event_bus_reader.py ack()` → old endpoint | `POST /events` with `event_type: 'ack'` | H |
| F20 | 591-601 | Old endpoint | `event_bus.py close` with --transitions, --comments | `event_bus.py ack <event_id>` | H |
| F21 | 467,472 | Old method | `close(event_id, role)` | `ack(event_id, role)` | M |
| F22 | 448 | Old event | `event-closed` event | ack = closed | M |
| F23 | 762-770 | Old endpoint | Phase 2: old endpoint + close() + boot_agent_with_event() | ack-only deliverables | H |
| F24 | 774 | Old endpoint | Success criteria: `POST /events/{id}/complete` | ack event | H |
| F25 | 821 | Old endpoint | Risk register: old endpoint reference | ack event | L |
| F26 | 843 | Old endpoint | Vault candidate: old endpoint | ack event | L |
| F27 | 651 | Old count | "14-event matrix" | 5-event model | L |
| F28 | 628 | Old event | "emit `stopped`" | "emit `ack`" — ack of stop-requested = stopped | H |
| F29 | 501 | Old L2 sub-skills | "Mechanical reactions" | No mechanical reactions; 5-event model has none | M |
| F30 | 623-632 | Old L2 context | event-reactions.md still describes per-event guidance | Only universal ack protocol + 5-event table | M |
| F31 | 375 | Contradiction | "REPLACED" but still in "New Endpoints" table | Remove or move to deprecated | L |
| F32 | 315 | Contradiction | "10 events behind queue tip" | 3 or reconceptualize for 5 events | L |
| F33 | 624 | Stale ref | Cross-ref to old Section 3.3 | Cross-ref to Section 3.2 | L |
| F34 | 287 | Old model | "Consumers determined by event type" | Emitter specifies target | L |
| F35 | 287 | Old mechanism | "Monitor tool detects file" | HTTP poll script + stdout | L |

## Side Effects

- **Risk 1**: An implementer reading Sections 5.1-5.3 without noticing the Section 3.2/3.3 update would implement the old 30+ event model with `POST /events/{id}/complete` endpoint and L2 event-reaction sub-skills — Severity: H — Mitigation: Add a prominent "UPDATED MODEL" banner at the top of Sections 5.1, 5.2, 5.3, and the Phasing Plan.
- **Risk 2**: The Phase 2 deliverables list contradicts itself: line 762 says "POST /events/{id}/complete endpoint" while line 375 says it's REPLACED — Severity: H — Mitigation: Rewrite entire Phase 2 section.

## Edge Cases

- **Ack semantics ambiguity**: If the agent emits `ack {event_id}` but the harness can't tell if work was actually done, is this a trust-based model? The old closure payload carried proof of work (transitions, comments). Clarify in PRD whether ack implies "I handled it" or requires additional verification.
- **Multi-agent ack coordination**: Section 3.2 says "Every event gets an ack." Section 3.3 Example 3 says "All agents update status line, each emits ack." The old multi-consumer tracking (consumer_status per role) still appears in the harness state model (line 414-419). Clarify whether multi-consumer ack tracking survives or is simplified.

## Integration Risks

- **Compose deployment integration**: Section 5.3 line 651 says "REMOVE: common/event-reactions" but event-reactions.md currently exists at `references/sub-skills/common/event-reactions.md` with the old 10-event table. Removing it from includes.yml but keeping the file is fine, but the file should be updated or archived to avoid confusion.
- **Event catalog divergence**: The actual `event_catalog.py` at `references/scripts/event_catalog.py` still has the old 12 EMITTED + 5 RECOGNIZED = 17 event types. The 5-event model's 5 types don't exist in the catalog. The PRD and codebase must converge.

## Upgrade & Migration

- **New config values**: No changes from current PRD — the 5 config values (event-driven, event-timeout-minutes, event-max-retries, event-poll-interval, event-queue-cap) are still valid.
- **New files**: `references/sub-skills/common/event-driven-workflow.md` still needed but its content outline (lines 560-621) must be rewritten to remove the old `event_bus.py close` command.
- **Template changes**: The 5 removed sub-skills are still correct. The includes.yml changes (line 648-653) are correct except for the "14-event matrix" reference.
- **Upgrade steps**: No change.
- **Graceful degradation**: No change — config gating still works.

## Open Questions

- **Q1**: Does the harness still track multi-consumer ack status per event (i.e., "event closed only when all target agents have acked"), or is each ack independent? — **Why**: The harness state model (line 414, 419) shows `consumers: {pm: "closed", skill: "pending"}` from the old model. Section 3.2 doesn't clarify whether `shipped` (sent to all agents) requires all agents to ack before it's "closed."
- **Q2**: Are the continuous monitors (git-watcher, tracker-watcher, health-watcher) still needed in the 5-event model, and if so, what events do they emit vs. what the harness translates? — **Why**: Section 5.1 lines 456-466 describes monitors emitting events. But the 5-event model only has 5 agent-facing event types. The translation layer between monitor outputs and agent-facing events is unspecified.
- **Q3**: How does an agent know what work to do when it receives `assigned-to {role, issue_or_pr}` if the event payload is just a pointer? — **Why**: Section 3.2 says "Forge is the source of truth" — agent reads the issue/PR from GitHub. But what if the agent needs additional context (e.g., which specific gaps QA found)? The old model included findings in the event payload. Clarify if the agent reads the forge for ALL context.

## Recommendation

**Needs rethinking of document consistency, not the architecture.** The 5-event model in Sections 3.2 and 3.3 is clean, well-reasoned, and correctly simplifies the architecture. But 22 other locations across the document contradict it. The PRD cannot be implemented from in its current state — an implementer would build the old model. 

**Priority fixes (block merging)**:
1. F17 — Section 5.1, item 1: DELETE the `POST /events/{id}/complete` implementation section (line 441-445)
2. F18-F20 — Sections 5.2-5.3: Replace all `event_bus.py close` and old-endpoint references with `ack` event
3. F23 — Phase 2 deliverables: Remove old endpoint + close function, replace with ack
4. F28 — Section 5.3 line 628: "emit `stopped`" → "emit `ack`"
5. F10-F11 — Sections 5.1-5.2: Clarify monitor events are harness-internal; add translation layer to 5 agent-facing events

**Secondary (fix before Phase 2 implementation)**:
- All 35 findings should be resolved

## Vault Candidates

- **Type**: learning — **Surgical PRD section updates create internal contradiction** — **Why**: Sections 3.2/3.3 were rewritten to the 5-event model but 22 other sections were not. Future PRD updates that change fundamental models should be accompanied by a full-document grep for old terminology and a consistency checklist. The prior PRD-AUDIT found different issues (L3/L4 labeling) but didn't catch these because the 5-event model hadn't been patched in yet.
- **Type**: decision — **5-event model: agent-facing events vs. harness-internal events** — **Why**: The clean separation between 5 agent-deliverable events and the harness-internal monitoring events (git-pull, new-commits, etc.) is a key architectural insight worth capturing. "Events are routing signals, not context carriers" (PRD line 293) is a design principle that should survive future event type additions.
- **Type**: pattern — **ack-as-universal-closure pattern** — **Why**: Replacing a dedicated closure endpoint with an `ack` event that's processed like any other event simplifies the API surface. This pattern (control signals as events in the same bus) could apply to future signaling needs (pause, resume, reconfigure).