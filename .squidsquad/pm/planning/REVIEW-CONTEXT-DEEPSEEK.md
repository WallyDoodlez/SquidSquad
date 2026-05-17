Now I have all the evidence needed for a thorough review. Here are my findings:

---

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 95–98 and 359–364
- **Severity**: error
- **Issue**: #8695's "dispatch gate" contradicts the locked "thin harness, no dispatch logic" decision. The locked architecture (line 41–44) says the harness has "zero tracker observation, zero dispatch logic, zero per-role queue knowledge" and "every event reaches every agent via one global stream." Yet #8695 (lines 95–98) describes the harness gating "outbound dispatch" of `assigned-to` / `status-transition` events, queuing pre-boot events per-role, and flushing on `bootup-complete`. The note at lines 359–364 attempts to reconcile by saying the gate is for "harness-originated events (e.g. `pr-merged`, `compose-completed`)" — but those events are already broadcast to every agent in the pure-broadcast model, so a per-role gate on them makes no sense. A per-role dispatch gate only makes sense if the harness is doing targeted dispatch, which contradicts the locked decision. The RESEARCH-harness-events.md §"Path to Add bootup-complete" (lines 203–206) explicitly frames this as a dispatch queue with a `_dispatch_to_agent()` function — dispatch logic the locked decision supersedes.
- **Evidence**: Locked decision §2 line 41–44: "harness is an event bus only. No tracker observation. No dispatch logic. No per-role queue knowledge." §5.2 line 334–338: "When outbound dispatch occurs (future code path or any code path that emits `assigned-to`/`status-transition` toward an agent): if `bootup_complete is False`, queue in `_pending_dispatch[role]`." RESEARCH-harness-events.md line 203–206: "Add per-role dispatch queue... `_dispatch_to_agent()`... flush `_pending_dispatch[role]` by calling `_dispatch_to_agent()`. "
- **Suggested fix**: Either (a) remove the dispatch gate from #8695 entirely — `bootup-complete` becomes purely informational (harness sets a flag, exposes it via `/agents/{role}`, but does no queuing/gating of any outbound events); or (b) if the locked decision intends to permit harness-originated lifecycle events (`pr-merged`, `compose-completed`) to be gated per-role, update the locked decision to explicitly distinguish "dispatch logic" from "lifecycle-event gating" and define which harness-emitted events are subject to the gate. The deliverable in §5.2 must then be stripped of all `assigned-to`/`status-transition` dispatch language, since those are agent-to-agent signals that the harness does not originate.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 117–119 (step 6), 387 (step 5), and entire §5.1 scope
- **Severity**: error
- **Issue**: No task in this bundle creates the agent-side event-listening mechanism. The architecture assumes agents "listen on the event stream" (§3.1 step 6: "Begin listening on event stream"; §5.3 step 5: "enter event-listening (Monitor or equivalent)"). Yet `event_poll.py` does not exist (RESEARCH-harness-events.md line 25: "`event_poll.py`... does not exist yet"), and no task's scope includes creating it. #8694 produces cursor management and forge-read fragments but not the polling/streaming mechanism that connects agents to the harness event bus. #8696 tells agents to "enter event-listening" but doesn't specify how. The RESEARCH-harness-events.md summary table (line 344) lists `event_poll.py` as a gap assigned to "#8694 + #8695" but neither task's final scope in CONTEXT.md includes creating it. Without an event-receiving mechanism, agents can emit events but cannot read them — the entire event-driven architecture has no agent-side read path.
- **Evidence**: CONTEXT.md §5.1 deliverables (lines 267–296) cover event-reactions, cursor management, forge-read, idle cooldown, comment handling, transition-on-handoff — none include the polling script or stream-reading mechanism. RESEARCH-harness-events.md line 25: "`event_poll.py`... does not exist yet in `references/scripts/`. It is a planned script for Phase 5." Line 301: the old #8694 scope listed `event_poll.py` as a new file; CONTEXT.md no longer lists it. Line 344: summary table assigns `event_poll.py` gap to "#8694 + #8695". CONTEXT.md §5.1 line 286: listed new file is `event-reactions.md` (instruction fragment), not `event_poll.py` (executable script).
- **Suggested fix**: Either (a) add `event_poll.py` (or equivalent agent-side event-stream reader) as an explicit deliverable to #8694 or #8695 scope, with acceptance criteria covering cursor-based polling, timeout, and stdout streaming; or (b) specify that agents use the existing `event_bus_reader.py` directly (referenced in RESEARCH-harness-events.md line 102 as "called from `cycle_pre.py:1019`") and add an events-mode fragment describing how to invoke it in a long-running listen loop. Either way, the agent-side read path must be a concrete deliverable.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 109–122 (§3.1) and 397–403 (§5.3 acceptance)
- **Severity**: error
- **Issue**: L1 boot workflow has no branch for event-bus unreachable despite claiming "failsafe" property. §3.1 step 5 says "Emit `bootup-complete` event (POST `/events`...)." Step 6 says "Begin listening on event stream." If the event bus (harness) is down, step 5 will fail and step 6 cannot proceed. The locked decision at line 93–94 claims L1 boot "survives a total event-bus failure because the path is forge-scan based" — but the forge scan is only steps 1–3. After that, the agent dead-ends. The acceptance criteria at line 400–401 explicitly require: "agent boots when event bus is unreachable (still scans tracker — failsafe property)" — but scanning the tracker alone isn't sufficient if the agent then fails trying to POST `bootup-complete`. The RESEARCH-compose-boot.md (line 485) explicitly calls out "harness is down" as a case L1 boot matters for. There is no retry, backoff, or degraded-mode instruction.
- **Evidence**: CONTEXT.md §3.1 steps 4–6: "Advance cursor to latest event id. Emit `bootup-complete` event (POST `/events`...). Begin listening on event stream." §5.3 acceptance line 400–401: "agent boots when event bus is unreachable (still scans tracker — failsafe property)." RESEARCH-compose-boot.md line 485: "L1 boot matters when: (a) agent crashed mid-task, (b) harness is down, (c) fresh agent start with no events pending." No retry logic or fallback exists in the specification.
- **Suggested fix**: Add to §3.1: after step 4 (advance cursor), branch on event-bus reachability. If reachable: emit `bootup-complete`, enter listen. If unreachable: enter a retry loop (e.g., exponential backoff, capped at some max interval) attempting to reach the harness; while retrying, optionally operate in degraded mode (process the pre-queued forge item directly without event coordination). Document that emitting `bootup-complete` is best-effort — if the harness is down, the agent proceeds with forge-direct work and emits `bootup-complete` when the harness becomes reachable.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 375 vs. RESEARCH-compose-boot.md lines 401 and 442
- **Severity**: warning
- **Issue**: L1 boot fragment placement contradicts RESEARCH recommendation. CONTEXT.md §5.3 line 375 places L1 boot at `references/sub-skills/common-events/l1-boot.md` and line 388 says "Slot at position 1 of every role's `includes-events.yml`" — implying events-mode only. But RESEARCH-compose-boot.md line 401 recommends `mode: both` and line 442 says "Mode: both (needed for both /loop and event-driven boots)." If L1 boot is events-mode only, /loop agents don't get the failsafe boot, which contradicts the RESEARCH's finding that L1 boot should replace the existing inline Step 1c for all roles (RESEARCH-compose-boot.md line 503–504: "all four roles should use the `common/l1-boot` sub-skill instead of their individual Step 1c patterns"). The CONTEXT.md never resolves whether L1 boot applies to both modes or events-only.
- **Evidence**: CONTEXT.md §5.3 line 375: `references/sub-skills/common-events/l1-boot.md`. Line 388: "Slot at position 1 of every role's `includes-events.yml`." RESEARCH-compose-boot.md line 401: `mode: both`. Line 442: "Mode: both (needed for both /loop and event-driven boots)." Line 503–504: "all four roles should use the `common/l1-boot` sub-skill instead of their individual Step 1c patterns."
- **Suggested fix**: Lock the decision: if L1 boot is events-mode only, update the locked-decision language in §2 to say "L1 boot is an events-mode failsafe" and remove the implication it's universally available. If L1 boot is truly shared (mode:both), move it to `references/sub-skills/common/l1-boot.md` (not `common-events/`), include it in `includes-loop.yml` too, and add the `mode: both` classification. The latter aligns with the RESEARCH recommendation.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 4, 33–35, 411–412, 598–603, and sequencing diagram lines 652–663
- **Severity**: error
- **Issue**: #8699 is listed as a hard prerequisite that gates #8697 start, but #8697's scope absorbs #8699. The header (line 4) lists #8699 as a "hard prereq." The sequencing diagram puts #8699 in the prerequisites box with "#8692 — singleton enforcement" and shows an arrow "both must SHIP" → then #8697 starts. But line 411–412 says #8699 is "folded into #8697 scope" and line 598–603 says "#8699 closes when #8697's new `common-events/` tree contains the canonical `event-driven-workflow` fragment(s)." This is circular: #8699 is both a blocker for #8697 AND resolved by #8697's own work. The diagram's arrow "both must SHIP" before #8697 is impossible if #8699 IS #8697's migration work.
- **Evidence**: Line 4: "Hard prereqs: #8692 (singleton enforcement), #8699 (event-driven-workflow source fragment)." Line 33–35: "Two prerequisites... must ship before any per-role flip of `event-driven: yes`." Lines 652–655: diagram box lists #8699 as a prerequisite, then arrow "both must SHIP" to #8697. Line 411–412: "Includes migration of the orphaned `event-driven-workflow` block into a real source fragment (#8699 prereq folded in here)." Line 598–603: "#8699 closes when #8697's... tree contains the canonical `event-driven-workflow` fragment(s)."
- **Suggested fix**: Remove #8699 from the hard-prerequisites list and prerequisite box in the sequencing diagram. Replace with: "#8699 is resolved internally by #8697 — the event-driven-workflow migration is a #8697 deliverable, not a separate gate." The only true hard prerequisite is #8692 (singleton enforcement). Update line 4 and the diagram accordingly. The "before any per-role flip of `event-driven: yes`" constraint still holds for #8692, and #8697 naturally must complete before any flip since it creates the events-mode tree.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 260–268 (#8694 scope) vs 370–387 (#8696 scope)
- **Severity**: warning
- **Issue**: #8694 claims scope over "The 5 workflow cases (boot / idle-event-arrives / after-completion / mid-task-event / special events) verbatim from §3" (line 270–271), while #8696 separately covers the boot case (Case A, §3.1). Both tasks produce fragments that describe boot behavior. The division of responsibility is unclear: does #8694's boot case fragment duplicate #8696's L1 boot, reference it, or handle a different aspect of boot? The CONTEXT.md never states how these fragments relate. If both produce boot instructions, the composed CLAUDE.md could contain contradictory or duplicated boot sequences.
- **Evidence**: CONTEXT.md §5.1 line 270–271: "The 5 workflow cases (boot / idle-event-arrives / after-completion / mid-task-event / special events) verbatim from §3." §5.3 line 370–372: "Implements Case A (§3.1)." Both claim §3.1 Case A (boot) as their domain. #8694's files (line 286) include `event-reactions.md` — is this expected to cover the boot case? #8696's files (line 391) include `l1-boot.md`. No explicit cross-reference between the two.
- **Suggested fix**: Add to §5.1 scope: "The boot case (Case A) is defined in #8696's `l1-boot.md` fragment. #8694's workflow fragments reference it but do not duplicate it. #8694 covers Cases B–E (idle-event-arrives, after-completion, mid-task-event, special events)." Or restructure so #8694 explicitly lists 4 cases (excluding boot) and references #8696 for boot.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 57–59 (atomicity rule) and 163–166 (improvement-scan as atomic task) and 65–66 (cool-down storage schema)
- **Severity**: warning
- **Issue**: Improvement-scan crash recovery is undefined. The atomicity rule says improvement-scan is an atomic task, meaning it runs to completion. On crash during improvement-scan, L1 boot (§3.1 step 1) reads working-state.md for "in-progress task." But improvement-scans are not tracker items — they have no issue number. The forge verification step (§3.1 step 2) can't find them. The working-state.md schema only defines `## Improvement Scan` with `Last completed: <ts>` and `Cool-down: 30m` — no `status: in-progress` field. The agent has no way to know if it crashed mid-scan and should resume or restart. Additionally, if the agent treats the crashed scan as lost and starts a new one, the atomicity guarantee is violated (partial scan results may have been committed).
- **Evidence**: §2 lines 57–59: "every task (real tracker work AND improvement-scan tasks) runs to completion." §3.6 lines 163–164: "enter improvement-scan as an atomic task." §3.1 step 1: "Read working-state.md → cursor + in-progress task." §3.1 step 2: "Verify in-progress against forge — still my role? still status:in-progress?" §2 lines 65–66: cool-down storage has only `Last completed` and `Cool-down` — no in-progress flag. No schema field for active improvement-scan task.
- **Suggested fix**: Add to `## Improvement Scan` schema: `Status: idle | running` (or similar). L1 boot §3.1 step 2: add "If the in-progress task is an improvement-scan (not a tracker item), skip forge verification and restart the scan (or resume from checkpoint if the scan supports checkpointing)." Alternatively, declare that crashed improvement-scans are simply restarted (the scan is idempotent by nature — it analyzes code quality and produces recommendations, and a fresh scan subsumes a partial one). Whichever approach, document the behavior.

---

### Finding 8

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 100–103 (event stream gap behavior and long cursor lag)
- **Severity**: warning
- **Issue**: The "event stream gap" and "long cursor lag (24h+)" policies assume events are still available in the stream, but the event stream is a bounded deque (maxlen=1000, RESEARCH-harness-events.md line 81–82: "in-memory only... deque, maxlen=1000"). If an agent's cursor is >1000 events behind, the events it hasn't processed have been evicted. `GET /events?since=<old_cursor_id>` will return either no results or only the most recent events (depending on implementation). The policies at lines 100–103 say "log warning, advance cursor past the gap" and "skim-then-advance for audit fidelity" — but there's nothing to skim. The agent must handle the "cursor references evicted events" case distinctly from a small in-stream gap.
- **Evidence**: CONTEXT.md line 100–101: "Event stream gap behavior — log warning, advance cursor past the gap, continue." Line 102–103: "Long cursor lag (24h+) — skim-then-advance for audit fidelity, not jump-to-latest." RESEARCH-harness-events.md line 81–82: "in-memory only. EventStream is a collections.deque(maxlen=1000)." Line 84: "No replay on harness restart. If the harness crashes, all events are lost."
- **Suggested fix**: Add a third gap scenario: "Eviction gap (cursor predates oldest event in stream) — the event stream cannot serve events at or before the cursor. Log warning with eviction details. Advance cursor to oldest-available event ID, then skim forward from there. Do not attempt to retrieve evicted events (they are gone; forge current state subsumes them)." Distinguish this from the "in-stream gap" which is a small missing range within the retained window.

---

### Finding 9

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 117–118 (payload field) and 321–322 (catalog entry)
- **Severity**: warning
- **Issue**: The `bootup-complete` event payload field `monitor_active` is undefined. §3.1 step 5 says the payload is `{"monitor_active": true}`. #8695 §5.2 line 321–322 says `payload_fields` is `["monitor_active"]`. But nowhere in the architecture is `monitor_active` defined — what does it mean? Is it a boolean indicating the agent's Monitor tool is running? If the event-listening mechanism isn't Monitor (see Finding 2), this field is misleading. The RESEARCH-harness-events.md (line 189) carries the same assumption: `{"monitor_active": true}` with the context "Monitor subscription active" — but the CONTEXT.md never commits to Monitor as the event-listening mechanism.
- **Evidence**: CONTEXT.md §3.1 line 117–118: `payload {"monitor_active": true}`. §5.2 line 321–322: `payload_fields ["monitor_active"]`. RESEARCH-harness-events.md line 189: `event_bus.emit("bootup-complete", role, {"monitor_active": true})` with comment "after Monitor subscription active." CONTEXT.md §3.1 step 6: "Begin listening on event stream" — no mention of Monitor. §5.3 step 5: "enter event-listening (Monitor or equivalent)" — "or equivalent" suggests Monitor is not locked.
- **Suggested fix**: Either (a) lock Monitor as the event-listening mechanism and define `monitor_active` as "boolean indicating the agent's event-stream listener is running and ready to receive events"; or (b) rename the field to `listener_active` or `event_stream_ready` to be mechanism-agnostic. Define the field semantics in the glossary (§11).

---

### Finding 10

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 334–338
- **Severity**: error
- **Issue**: #8695 deliverable text still describes harness dispatch of `assigned-to` and `status-transition` events, which contradicts the locked thin-harness decision (see Finding 1). The deliverable at lines 334–338 says: "When outbound dispatch occurs (future code path or any code path that emits `assigned-to`/`status-transition` toward an agent): if `bootup_complete is False`, queue in `_pending_dispatch[role]`." The locked architecture says agents themselves run `work_queue()` (line 23) and "harness has zero dispatch logic" (line 42). If the harness doesn't emit `assigned-to` or `status-transition` toward agents, this gating code has nothing to gate. The note at lines 359–364 clarifies the gate is for harness-originated events like `pr-merged` and `compose-completed` — but the deliverable text at lines 334–338 says `assigned-to`/`status-transition`, not `pr-merged`/`compose-completed`.
- **Evidence**: Line 334–338: "When outbound dispatch occurs (future code path or any code path that emits `assigned-to`/`status-transition` toward an agent): if `bootup_complete is False`, queue in `_pending_dispatch[role]`." Line 359–364: "the 'dispatch gate' is primarily a guard for any *external* sources of harness-originated events (e.g. `pr-merged`, `compose-completed` via `_emit_event()` already in `harness.py`)." These reference different event types. `assigned-to` and `status-transition` are agent-to-agent signals; `pr-merged` and `compose-completed` are harness lifecycle events.
- **Suggested fix**: Align the deliverable text with the note. Change lines 334–338 to reference only harness-originated event types (`pr-merged`, `compose-completed`, and any other events `_emit_event()` produces). Remove `assigned-to` and `status-transition` from the gating description since the harness does not emit those. If the harness will never emit `assigned-to`, remove it from the event catalog's EMITTED dict for harness source.

---

### Finding 11

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 246–247
- **Severity**: warning
- **Issue**: L4 project instructions are declared "mode-agnostic" but may contain /loop-referencing language that would confuse events-mode agents. The CONTEXT.md doesn't address whether L4 files need review for /loop contamination. If `.squidsquad/project/shared-instructions.md` or `<role>-instructions.md` reference cycle mechanics (e.g., "at the end of your cycle," "during cycle_post," "check your next cycle"), an events-mode agent receiving these instructions would be given contradictory guidance — violating the "no mode-conditional logic" principle at the L4 layer even if L1–L3 are clean.
- **Evidence**: CONTEXT.md §4.3 line 246–247: "L4 project instructions (`.squidsquad/project/`) are mode-agnostic and continue to flow through the existing Layer 4 mechanism." RESEARCH-compose-boot.md lines 33–35: lists `.squidsquad/project/pm-instructions.md`, `dev-instructions.md`, `shared-instructions.md` as L4 files. No review or filtering of these files is mentioned in any Phase 5 task.
- **Suggested fix**: Add to #8697 scope or create a checklist item: "Review all L4 project instruction files for /loop-specific language. Any `/loop` references must be either removed, generalized, or split into loop/events variants (with corresponding compose.py logic)." Or note this as a pre-flip checklist item in §6.

---

### Finding 12

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 479–481
- **Severity**: warning
- **Issue**: #8700's backward-compat "detect per-role wake mode" is underspecified. The status line must know whether each role is in /loop or events mode to decide between HTTP API and file-based rendering. The CONTEXT.md doesn't specify how this detection works. Options: read `config.md` per role, query harness API for `bootup_complete` flag, or check for existence of event-driven artifacts. Each has edge cases: `config.md` says `event-driven: yes` but the agent hasn't been deployed yet; `bootup_complete` is a runtime flag that's `False` until the agent boots; file-based artifacts may exist in both modes during transition. Without specification, the implementer may make an incorrect choice.
- **Evidence**: CONTEXT.md §5.5 line 479–481: "Backward compat: detect per-role wake mode. For /loop roles during transition, fall back to file-based rendering." No mechanism specified. RESEARCH-harness-events.md API list (lines 40–52): `/agents/{role}` returns `AgentState` which after #8695 will include `bootup_complete`. But `bootup_complete` is not a reliable proxy for `event-driven: yes` (a role could be events-mode but the agent hasn't booted).
- **Suggested fix**: Specify the detection mechanism. Recommended: read `event-driven: yes/no` from `.squidsquad/config.md` for the role (same mechanism `compose.py` uses via `_read_config_value()`). This is the authoritative config gate, and the status line can independently read it. Document the edge case: if config says `yes` but the agent hasn't booted (no health data), show "events-mode, not yet booted."

---

### Finding 13

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 544–571 and 486–488
- **Severity**: warning
- **Issue**: The "TUI" referenced in both #8700 (status line) and #8704 (human queue panel) is never defined as a concrete component. #8700 says "Status line script(s) (location per current codebase — likely a `statusline.py` or similar in `references/scripts/`)" and #8704 says "TUI / status display script(s)" — both vague. Are these the same display? Different panels of one terminal UI? Separate scripts? The CONTEXT.md doesn't establish whether there's a single TUI process, separate scripts that each render independently, or a harness-hosted dashboard. This ambiguity could lead to inconsistent implementations.
- **Evidence**: CONTEXT.md §5.5 line 486–488: "Status line script(s) (location per current codebase — likely a statusline.py or similar in references/scripts/)." §5.7 line 564: "TUI / status display script(s)." No architectural definition of the display surface. §3.8 line 197: "Harness TUI surfaces human-assigned work prominently" — implies a single TUI. But does the TUI belong to the harness process or is it standalone?
- **Suggested fix**: Add a brief architectural note: is there one TUI process or multiple? Does the harness serve a TUI (e.g., terminal dashboard) or do separate scripts render independently? Cross-reference between #8700 and #8704: do they share a refresh loop? If they're the same TUI, say so explicitly and merge the display deliverables.

---

### Finding 14

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 65–66 (cool-down storage schema) and 111–113 (L1 boot step 1–2)
- **Severity**: warning
- **Issue**: The cool-down storage schema lacks an "in-progress" status field, making crash recovery ambiguous (related to Finding 7). The schema at lines 65–66 specifies `Last completed: <ts>` and `Cool-down: 30m` but no `Status: running | idle` field. The `Last completed` field is written only AFTER scan completion (line 165–166). On crash during scan, `Last completed` still holds the previous scan's timestamp, and the agent can't distinguish "crashed mid-scan" from "no scan running." Additionally, the "Cool-down" field is a static config value stored in working-state.md — but config changes (e.g., a human changes `config.md` to override cool-down) wouldn't be reflected unless the agent re-reads config.md, which isn't specified.
- **Evidence**: CONTEXT.md §2 lines 65–66: "fields: `Last completed: <ts>`, `Cool-down: 30m`." §3.6 lines 165–166: write after scan completes. §3.6 line 168: `Cool-down: 30m` — hardcoded in working-state.md rather than read from config.md. §3.1 step 1: reads working-state.md for "in-progress task" — no improvement-scan status field to read.
- **Suggested fix**: Add `Status: idle | running` to the `## Improvement Scan` schema. Write `Status: running` when scan begins, `Status: idle` + `Last completed: <ts>` when scan completes. L1 boot checks `Status: running` → scan was interrupted → restart scan (or declare idempotent and start fresh). Alternatively, note that improvement scans are idempotent and always restarted on crash — but document this explicitly. For the `Cool-down` value: specify it is read from `config.md` at scan-completion time and written to working-state.md for the sleep timeout calculation, so config changes take effect on the next scan boundary.

---

### Finding 15

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 339 (line 340 reference to `AgentState.to_dict()`)
- **Severity**: warning
- **Issue**: #8695 acceptance criteria list integration tests for pre-boot dispatch queuing and delivery, but the locked architecture says the harness has no dispatch. The acceptance criteria at lines 355–356 state: "Integration test: a pre-boot dispatch is queued and delivered after `bootup-complete`." This presupposes dispatch exists. If the architecture is pure broadcast with no dispatch (as locked), this test is meaningless — there's no queue to test. If the architecture permits harness-originated lifecycle events to be queued, the test should reference those event types specifically.
- **Evidence**: CONTEXT.md §5.2 line 355–356: "Integration test: a pre-boot dispatch is queued and delivered after `bootup-complete`." Line 42: "No dispatch logic." The acceptance criterion uses the word "dispatch" generically but the locked decision bans dispatch logic.
- **Suggested fix**: Reword the integration test to: "Integration test: a harness-originated event (e.g., `compose-completed`) emitted while a role's `bootup_complete` is `False` is held and delivered after the role emits `bootup-complete`." Or remove the integration test if the harness no longer queues events per-role (per Finding 1's suggested fix).

---

### Finding 16

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 141–142
- **Severity**: warning
- **Issue**: The parenthetical at line 141–142 says the after-completion flow "replaces the original RESEARCH framing where the harness pushes the next `assigned-to`." But the RESEARCH framing was for #8694's original dispatch-on-handoff scope. CONTEXT.md §5.1 has re-scoped #8694 to agent-side reactions only (removing dispatch logic). This creates a gap: the RESEARCH's open questions at RESEARCH-harness-events.md lines 307–319 (how harness learns role ownership, duplicate dispatch avoidance, empty queue behavior, event_poll.py details, singleton interaction, bootstrap timeout, `--target` flag semantics, coordination with config flip) are never explicitly resolved or declared moot in CONTEXT.md. Some are moot under thin-harness, but others (like #8692 singleton interaction at line 315–316, and `event_poll.py` existence at line 319) remain relevant. The CONTEXT.md should explicitly close each open question.
- **Evidence**: CONTEXT.md line 141–142: "(This replaces the original RESEARCH framing where the harness pushes the next `assigned-to`.)" RESEARCH-harness-events.md lines 307–319: 8 open questions, many now moot or unresolved. CONTEXT.md §10 lists 5 open questions — none of them address the RESEARCH questions.
- **Suggested fix**: Add a §10 item or a closing note: "RESEARCH open questions 1–4 and 7–8 are moot under the thin-harness no-dispatch architecture. Question 5 (singleton enforcement interaction) is resolved by #8692 being a hard prerequisite. Question 6 (bootstrap timeout during harness restart) is unresolved — add to open questions or lock a default timeout (e.g., 60s watchdog that clears the gate)."

---

### Finding 17

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 63 (cool-down default) and 715 (open question #1)
- **Severity**: warning
- **Issue**: The locked decision at line 63–64 says "Cool-down default = 30 minutes universal across roles, overridable per-role in `config.md` (no overrides until empirical observation warrants)." But open question #1 (line 718–720) asks: "Confirm: no role-specific overrides ship in v1?" This is already answered by the locked decision's parenthetical. The open question is redundant — the decision is locked. If the PM still needs to confirm, the decision isn't actually locked. This is a minor inconsistency.
- **Evidence**: Line 63–64: "(no overrides until empirical observation warrants)." Line 718–720: "Cool-down per-role overrides — leave config.md schema empty until empirical observation warrants tuning. Confirm: no role-specific overrides ship in v1?"
- **Suggested fix**: Either remove open question #1 (it's already decided) or change the locked decision to "pending confirmation" and keep the question. The locked decision and the open question should not both exist in contradictory states.

---

### Finding 18

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 608–610 (Phase 6 soak gate)
- **Severity**: warning
- **Issue**: The Phase 6 soak criterion at lines 608–610 says "event-driven operation has been observed stable for a tunable soak period." Open question #5 (line 731–732) asks "how long does event-driven operation need to be stable before #8698 / #8702 are picked up? Not locked." But the soak period being "tunable" and "not locked" creates a sequencing risk: if the period isn't defined before Phase 5 completes, Phase 6 can't start because no one knows when the gate opens. The open question should be resolved before Phase 5 rollout completes so there's a concrete exit criterion.
- **Evidence**: Line 608–610: "stable for a tunable soak period." Line 731–732: "Soak period before Phase 6 — how long does event-driven operation need to be stable before #8698 / #8702 are picked up? Not locked."
- **Suggested fix**: Lock a minimum soak period (e.g., "2 weeks of stable operation across all roles with zero event-processing incidents") with the understanding it can be extended if issues arise. Or explicitly state: "The soak period is gated on PM judgment at Phase 5 completion; no fixed duration is predefined." Either way, remove the ambiguity — "tunable" and "not locked" is not actionable for downstream sequencing.

---

### Finding 19

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 72–73 (DM comment re-read timing)
- **Severity**: warning
- **Issue**: The DM exception says "DM re-reads comments at task completion before next pickup." But the DM's "task" during PR-merge wait is a long-running wait — not active work. The atomicity rule says the task runs to completion. Does "task completion" mean when the PR merges (end of wait), or does the DM periodically re-read comments during the wait? The wording "at task completion" suggests only at the end, but the justification says "PR-merge wait can be long; comment-driven guidance... must be honored" — which implies more frequent re-reading would be beneficial. This is ambiguous.
- **Evidence**: CONTEXT.md §3.7 line 70–73: "DM's task includes waiting for PR merges; comments may land during the wait. DM re-reads comments at task completion before next pickup." §2 line 57–59: "every task... runs to completion. Mid-task events are read and cursor-advanced but not acted on until the current task ends."
- **Suggested fix**: Clarify: does "task completion" mean the PR-merge completes (the wait ends), or does the DM have a sub-loop that periodically re-reads comments during the wait? If the former, a comment asking DM to reassign during a 2-hour PR-merge wait would be ignored for 2 hours. If the latter, describe the sub-loop: "During PR-merge wait, DM periodically (e.g., every 5 minutes) re-reads issue comments without advancing any cursor. If guidance is found, DM acts on it (reassign, route-back, file follow-up) as a sub-action within the atomic wait task."

---

I have 19 findings. Let me ensure I'm not missing anything critical by re-checking the original review criteria:

1. **Correctness against ACs**: Finding 1, 2, 3, 5, 10 are correctness issues.
2. **Regressions**: Not applicable (planning doc, not code).
3. **Edge cases**: Findings 7 (crash during improvement-scan), 8 (cursor eviction), 3 (event bus unreachable), 11 (L4 /loop contamination), 14 (cool-down crash recovery) cover edge cases.
4. **Integration**: Findings 6 (#8694 vs #8696 overlap), 13 (TUI undefined), 4 (L1 boot placement), 12 (#8700 mode detection) cover integration concerns.
5. **Philosophy violations**: Findings 1, 10 (dispatch gate vs thin harness), 11 (L4 mode-agnostic but potentially contaminated), 16 (unresolved RESEARCH questions).

I think 19 findings is comprehensive without being nitpicky. Let me finalize.Now I have all the cross-referencing evidence. Here are my findings:

---

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 41–44 vs. 95–98 and 334–338
- **Severity**: error
- **Issue**: #8695's "dispatch gate" contradicts the locked thin-harness decision. The locked decision (line 41–44) states the harness has "zero dispatch logic" and "zero per-role queue knowledge." But §2 line 95–98 says "harness must NOT push `assigned-to` / `status-transition` events to a role until that role has emitted `bootup-complete`. Pre-bootup events queue per-role and flush on receipt." And §5.2 lines 334–338 describe a `_pending_dispatch[role]` queue gating `assigned-to`/`status-transition` toward an agent. This IS dispatch logic. The note at lines 359–364 tries to reconcile by saying the gate is for harness-originated events (`pr-merged`, `compose-completed`), but those event types are different from `assigned-to`/`status-transition`, and a per-role gate on broadcast events makes no sense in a pure-broadcast model. The RESEARCH-harness-events.md lines 203–206 explicitly frame this as a `_dispatch_to_agent()` function — dispatch logic the locked decision claims to supersede.
- **Evidence**: CONTEXT.md line 42: "No dispatch logic. No per-role queue knowledge." Line 95–98: "harness must NOT push assigned-to / status-transition events to a role until... bootup-complete. Pre-bootup events queue per-role and flush on receipt." Line 334–338: "When outbound dispatch occurs... that emits assigned-to/status-transition toward an agent... queue in _pending_dispatch[role]." RESEARCH-harness-events.md line 203–206: "Add per-role dispatch queue... _dispatch_to_agent()... flush _pending_dispatch[role] by calling _dispatch_to_agent()."
- **Suggested fix**: Either (a) remove the dispatch gate from #8695 entirely — `bootup-complete` becomes an informational flag exposed via `GET /agents/{role}` with no queuing/gating logic; or (b) if the architecture permits harness-originated lifecycle events to be gated, explicitly list which event types (`pr-merged`, `compose-completed`) are subject to the gate, strip all `assigned-to`/`status-transition` language from #8695, and update the locked decision to distinguish "agent-to-agent dispatch" (forbidden) from "harness-lifecycle-event gating" (permitted).

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 119 (step 6), 387 (step 5), and scope of all tasks in bundle
- **Severity**: error
- **Issue**: No task in this bundle creates the agent-side event-listening mechanism. Agents must "listen on the event stream" (§3.1 step 6) and "enter event-listening" (§5.3 step 5). Yet `event_poll.py` does not exist (RESEARCH-harness-events.md line 25), and no task's scope includes creating it. #8694's deliverables cover cursor management, forge-read, idle cooldown, comment handling — but not the polling/streaming mechanism that connects agents to the event bus. The RESEARCH-harness-events.md summary table (line 344) assigned `event_poll.py` to "#8694 + #8695" but CONTEXT.md's re-scoped #8694 and #8695 no longer include it. Without a read path, the entire event-driven architecture has no way for agents to receive events.
- **Evidence**: CONTEXT.md §5.1 deliverable files (lines 286–296): `event-reactions.md`, `cursor-management.md`, `forge-read-pattern.md`, `idle-cooldown-loop.md`, `comment-handling.md` — no `event_poll.py` or equivalent. RESEARCH-harness-events.md line 25: "`event_poll.py`... does not exist yet." Line 301: old #8694 scope listed `event_poll.py` as new file; CONTEXT.md no longer lists it. Line 344: summary table assigns gap to "#8694 + #8695." §5.2 and §5.5 deliverables: harness-side only, no agent-side read script.
- **Suggested fix**: Either (a) add `event_poll.py` as an explicit deliverable to #8694 (scripts touched: `references/scripts/event_poll.py`) with acceptance criteria for cursor-based polling, timeout support, and stdout JSON-lines streaming; or (b) specify that agents use the existing `event_bus_reader.py` directly (RESEARCH-harness-events.md line 102) and add an events-mode instruction fragment describing how to invoke it in a long-running listen loop with cursor advancement.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 109–122 (§3.1) and 397–402 (§5.3 acceptance)
- **Severity**: error
- **Issue**: L1 boot workflow has no branch for event-bus unreachable, contradicting the "failsafe" claim. §3.1 steps 4–6 mandate emitting `bootup-complete` via POST `/events` and then "begin listening on event stream." If the harness is down, step 4 fails and step 5 cannot proceed. Yet the locked decision (line 93–94) says L1 boot "survives a total event-bus failure because the path is forge-scan based" and the acceptance criteria (line 400–401) require: "agent boots when event bus is unreachable (still scans tracker — failsafe property)." The forge scan is only steps 1–3; after that, the agent dead-ends. RESEARCH-compose-boot.md line 485 explicitly lists "harness is down" as a case L1 boot must handle.
- **Evidence**: CONTEXT.md §3.1 steps 4–6: "Advance cursor to latest event id. Emit bootup-complete event (POST /events...). Begin listening on event stream." Line 93–94: "L1 boot is tracker-driven failsafe... survives a total event-bus failure." Line 400–401: "agent boots when event bus is unreachable (still scans tracker — failsafe property)." No retry, backoff, or degraded-mode branch exists.
- **Suggested fix**: Add to §3.1 after step 4: branch on event-bus reachability. If reachable: emit `bootup-complete`, enter listen. If unreachable: enter a retry loop (e.g., exponential backoff capped at 5 minutes) attempting to reach the harness; while waiting, operate in degraded mode by processing the pre-queued forge item directly. Document that `bootup-complete` emission is best-effort — the agent proceeds with forge-direct work and emits it later when the harness becomes reachable. Add an acceptance criterion: "agent boots when event bus is unreachable: completes forge scan, enters retry loop, does NOT crash or hang."

---

### Finding 4

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 375 and 388 vs. RESEARCH-compose-boot.md lines 401 and 442
- **Severity**: warning
- **Issue**: L1 boot fragment placement contradicts RESEARCH recommendation. CONTEXT.md §5.3 line 375 places L1 boot in `references/sub-skills/common-events/l1-boot.md` and line 388 slots it only in `includes-events.yml` — making it events-mode only. But RESEARCH-compose-boot.md line 401 shows `mode: both` and line 442 says "Mode: both (needed for both /loop and event-driven boots)." The RESEARCH also recommends L1 boot replace existing inline Step 1c for all four roles (line 503–504), which requires it be available in /loop mode too. CONTEXT.md never resolves this: is L1 boot events-mode only or truly shared?
- **Evidence**: CONTEXT.md §5.3 line 375: `references/sub-skills/common-events/l1-boot.md`. Line 388: "Slot at position 1 of every role's includes-events.yml." RESEARCH-compose-boot.md line 401: `mode: both`. Line 442: "Mode: both (needed for both /loop and event-driven boots)." Line 503–504: "all four roles should use the common/l1-boot sub-skill instead of their individual Step 1c patterns."
- **Suggested fix**: Lock the decision. If L1 boot is events-only, move the file path to `common-events/`, note that /loop agents retain their existing Step 1c, and update the RESEARCH reference. If L1 boot is truly shared, move it to `references/sub-skills/common/l1-boot.md`, add it to both manifest variants, and update §5.3 deliverables to include `includes-loop.yml` entries. The latter aligns with the RESEARCH and gives /loop agents the failsafe benefit.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 4, 33–35, 411–412, 598–603, and sequencing diagram lines 652–663
- **Severity**: error
- **Issue**: #8699 is listed as a hard prerequisite that must ship before #8697, but #8697's scope absorbs #8699 — creating a circular dependency. Line 4 lists #8699 as a hard prereq. The sequencing diagram (lines 652–663) puts #8699 in the prerequisites box with an arrow "both must SHIP" before #8697 starts. But line 411–412 says #8699 is "folded into #8697 scope" and line 598–603 says "#8699 closes when #8697's... tree contains the canonical event-driven-workflow fragment(s)." #8699 cannot both gate #8697 and be resolved by #8697.
- **Evidence**: Line 4: "Hard prereqs: #8692 (singleton enforcement), #8699 (event-driven-workflow source fragment)." Lines 652–659: diagram box lists #8699 in prerequisites, arrow "both must SHIP" → #8697. Line 411–412: "Includes migration of the orphaned event-driven-workflow block into a real source fragment (#8699 prereq folded in here)." Line 598–603: "#8699 closes when #8697's new common-events/ tree contains the canonical event-driven-workflow fragment(s) and compose.py deploy correctly emits it."
- **Suggested fix**: Remove #8699 from the hard-prerequisites list and from the prerequisite box in the sequencing diagram. Replace with a note: "#8699 is resolved internally by #8697 — the event-driven-workflow migration is a #8697 deliverable, not a separate gate." The only true hard prerequisite is #8692. Update line 4 and the diagram arrows accordingly.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 260–271 (#8694 scope) and 370–387 (#8696 scope)
- **Severity**: warning
- **Issue**: #8694 and #8696 both claim scope over the boot workflow (Case A from §3.1) without defining their relationship. #8694 says its scope includes "The 5 workflow cases (boot / idle-event-arrives / after-completion / mid-task-event / special events) verbatim from §3" (line 270–271). #8696 says it "Implements Case A (§3.1)" (line 371–372). Both produce fragments. If both produce boot instructions, the composed CLAUDE.md could contain duplicated or contradictory boot sequences. No cross-reference or division of responsibility is stated.
- **Evidence**: §5.1 line 270–271: "The 5 workflow cases (boot / idle-event-arrives / after-completion / mid-task-event / special events) verbatim from §3." §5.3 line 371–372: "Implements Case A (§3.1)." #8694 deliverable files (line 286) include `event-reactions.md` — should this cover boot? #8696 deliverable files (line 391) include `l1-boot.md`. No statement like "#8694's boot case references #8696's L1 boot fragment."
- **Suggested fix**: Add to §5.1 scope: "The boot case (Case A) is owned by #8696's `l1-boot.md` fragment. #8694's workflow fragments cover Cases B–E and reference but do not duplicate boot. #8694 produces the event-reaction logic that follows boot." Or restructure so #8694 explicitly lists 4 cases (excluding boot) and notes that boot is #8696's responsibility.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 57–59, 65–66, 111–113, 163–166
- **Severity**: warning
- **Issue**: Improvement-scan crash recovery is undefined. The atomicity rule (line 57–59) says improvement-scan is an atomic task. On crash during scan, L1 boot §3.1 step 1 reads working-state.md for an "in-progress task" and step 2 verifies it against the forge. But improvement-scans are not tracker items — they have no issue number and won't be found on the forge. The working-state.md schema (line 65–66) only defines `Last completed: <ts>` and `Cool-down: 30m` — no `Status: running | idle` field. The agent cannot distinguish "crashed mid-scan" from "no scan running."
- **Evidence**: §2 line 57–59: "every task (real tracker work AND improvement-scan tasks) runs to completion." §3.6 line 163–164: "enter improvement-scan as an atomic task." §3.1 step 1: "Read working-state.md → cursor + in-progress task." Step 2: "Verify in-progress against forge — still my role? still status:in-progress?" §2 line 65–66: schema has `Last completed` and `Cool-down` only — no status field. §3.6 line 165–166: write happens only after scan completes.
- **Suggested fix**: Add `Status: idle | running` to the `## Improvement Scan` schema. Write `Status: running` when scan begins, `Status: idle` + `Last completed: <ts>` on completion. L1 boot §3.1 step 2: add branch — "If the in-progress task is an improvement-scan (detected via `Status: running`), skip forge verification and restart the scan (improvement scans are idempotent — a fresh scan subsumes a partial one)."

---

### Finding 8

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 100–103
- **Severity**: warning
- **Issue**: Gap policies assume events are still in the stream, but the event stream is a bounded deque (maxlen=1000, RESEARCH-harness-events.md line 81–82). If an agent's cursor is >1000 events behind, the referenced events have been evicted. The policies at lines 100–101 ("log warning, advance cursor past the gap") and 102–103 ("skim-then-advance for audit fidelity") both assume retrievable events. `GET /events?since=<evicted_id>` returns nothing useful. No distinct handling for the "eviction gap" case exists.
- **Evidence**: CONTEXT.md line 100–101: "Event stream gap behavior — log warning, advance cursor past the gap, continue." Line 102–103: "Long cursor lag (24h+) — skim-then-advance for audit fidelity, not jump-to-latest." RESEARCH-harness-events.md line 81–82: "in-memory only. EventStream is a collections.deque(maxlen=1000)." Line 84: "No replay on harness restart. If the harness crashes, all events are lost."
- **Suggested fix**: Add a third scenario: "Eviction gap (cursor predates oldest retained event) — the event stream cannot serve events at the cursor position. Log warning with eviction details (oldest available event ID, number of events lost). Advance cursor to the oldest-available event ID, then skim forward from there. Forge current state subsumes any information lost from evicted events."

---

### Finding 9

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 117–118 and 321–322
- **Severity**: warning
- **Issue**: The `bootup-complete` payload field `monitor_active` is never defined. §3.1 step 5 says payload is `{"monitor_active": true}` and §5.2 line 321–322 says `payload_fields` is `["monitor_active"]`. But "Monitor" may not be the event-listening mechanism (Finding 2 shows it's unspecified), and `monitor_active` is not defined in the glossary (§11). The RESEARCH-harness-events.md line 189 uses this field with the context "Monitor subscription active" — but CONTEXT.md never commits to Monitor.
- **Evidence**: CONTEXT.md §3.1 line 117–118: `payload {"monitor_active": true}`. §5.2 line 321–322: `payload_fields ["monitor_active"]`. §3.1 step 6: "Begin listening on event stream" — no mention of Monitor. §5.3 step 5: "enter event-listening (Monitor or equivalent)" — "or equivalent" implies Monitor is not locked. Glossary §11: no `monitor_active` entry.
- **Suggested fix**: Either (a) lock Monitor as the mechanism and define `monitor_active` in the glossary as "boolean indicating the agent's event-stream listener is active and ready"; or (b) rename the field to `listener_active` or `event_stream_ready` to be mechanism-agnostic and define it accordingly.

---

### Finding 10

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 334–338 vs. 359–364
- **Severity**: error
- **Issue**: #8695 deliverable text references `assigned-to`/`status-transition` as the gated events, but the clarifying note references different event types (`pr-merged`, `compose-completed`). The deliverable at lines 334–338 says the gate applies "when outbound dispatch occurs... that emits `assigned-to`/`status-transition` toward an agent." The note at lines 359–364 says the gate is for "harness-originated events (e.g. `pr-merged`, `compose-completed` via `_emit_event()`)." These are different event categories. If the harness doesn't emit `assigned-to`/`status-transition`, the gate described in the deliverable has nothing to gate.
- **Evidence**: Line 334–338: "When outbound dispatch occurs... that emits `assigned-to`/`status-transition` toward an agent: if bootup_complete is False, queue in _pending_dispatch[role]." Line 359–364: "the 'dispatch gate' is primarily a guard for any *external* sources of harness-originated events (e.g. pr-merged, compose-completed via _emit_event() already in harness.py)."
- **Suggested fix**: Align the deliverable with the note. Change lines 334–338 to reference only harness-originated event types. Replace "`assigned-to`/`status-transition`" with "`pr-merged`, `compose-completed`, and any other event types emitted by `_emit_event()` in `harness.py`." Remove `assigned-to` from the `EMITTED` dict for harness source in #8695's event_catalog.py change.

---

### Finding 11

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 246–247
- **Severity**: warning
- **Issue**: L4 project instructions are declared "mode-agnostic" but may contain /loop-referencing language. If `.squidsquad/project/shared-instructions.md` or `<role>-instructions.md` reference cycle mechanics (e.g., "during your next cycle," "at cycle end"), events-mode agents receiving those instructions would get contradictory guidance — violating the "no mode-conditional logic" principle at the L4 layer. No task in the bundle includes a review or filtering of L4 files for /loop contamination.
- **Evidence**: CONTEXT.md §4.3 line 246–247: "L4 project instructions (.squidsquad/project/) are mode-agnostic and continue to flow through the existing Layer 4 mechanism." RESEARCH-compose-boot.md lines 33–35: lists `.squidsquad/project/pm-instructions.md`, `dev-instructions.md`, `shared-instructions.md` as L4 files. No review step in any Phase 5 task.
- **Suggested fix**: Add to #8697 scope or as a pre-flip checklist item in §6: "Audit all L4 project instruction files for /loop-specific language. Any cycle/loop references must be removed, generalized, or documented as needing split before a role's event-driven flip."

---

### Finding 12

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 479–481
- **Severity**: warning
- **Issue**: #8700's backward-compat mode detection mechanism is unspecified. The status line must "detect per-role wake mode" to decide between HTTP API and file-based rendering. No detection mechanism is specified. Options have edge cases: reading `config.md` may not reflect deploy state; checking harness `bootup_complete` flag is a runtime state that's `False` until the agent boots; file-based artifact detection may exist in both modes during transition.
- **Evidence**: §5.5 line 479–481: "Backward compat: detect per-role wake mode. For /loop roles during transition, fall back to file-based rendering." No detection mechanism specified. RESEARCH-harness-events.md lists `GET /agents/{role}` returning `AgentState` which after #8695 includes `bootup_complete` — but this is a runtime flag, not a config indicator.
- **Suggested fix**: Specify the detection mechanism. Recommended: read `event-driven: yes/no` from `.squidsquad/config.md` for the role (using the same mechanism `compose.py` uses). Document the edge case: if config says `yes` but the agent hasn't booted (no health data from harness), show "events-mode, awaiting boot."

---

### Finding 13

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 486–488 and 544–571
- **Severity**: warning
- **Issue**: The "TUI" referenced by both #8700 and #8704 is never defined as a concrete component. #8700 references "Status line script(s) (location per current codebase — likely a statusline.py or similar)" and #8704 references "TUI / status display script(s)." Are these the same display surface? Separate scripts? A single process? The relationship between the status line (#8700) and the human-queue panel (#8704) is undefined, risking inconsistent implementations.
- **Evidence**: CONTEXT.md §5.5 line 486–488: "Status line script(s) (location per current codebase — likely a statusline.py or similar in references/scripts/)." §5.7 line 564: "TUI / status display script(s)." §3.8 line 197: "Harness TUI surfaces human-assigned work prominently — see #8704." No architectural definition of how these relate.
- **Suggested fix**: Add a brief architectural note to §5.7 or a new §5.8: define whether there is one unified TUI process or separate scripts. If unified, state that #8700 and #8704 deliver panels within the same TUI, share a refresh loop, and should be implemented together. If separate, define the boundaries clearly.

---

### Finding 14

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 65–66 and 168
- **Severity**: warning
- **Issue**: The cool-down duration is stored as a static value in working-state.md (`Cool-down: 30m`, line 168) rather than read from `config.md`. The locked decision (line 63–64) says cool-down is "overridable per-role in `config.md`." If the value is hardcoded in working-state.md at scan-completion time, a config.md change won't take effect until the next scan completes and writes the new value. This may be intentional (config changes take effect on next scan boundary) but isn't documented. Additionally, `Cool-down` belongs in config, not in state — only the expiry timestamp (`Next scan after: <ts>`) should be in state.
- **Evidence**: §2 line 63–64: "overridable per-role in config.md (no overrides until empirical observation warrants)." §3.6 line 168: `Cool-down: 30m` — written to working-state.md at scan completion. No instruction to read from config.md at that moment.
- **Suggested fix**: Specify that at scan-completion time, the agent reads `config.md` for the current cool-down value (default 30m if absent), computes `Next scan after: <now + cooldown>`, and writes only the expiry timestamp to working-state.md. Remove the static `Cool-down` field from the schema; replace with `Next scan after: <ts>`.

---

### Finding 15

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 355–356
- **Severity**: warning
- **Issue**: #8695 acceptance test assumes dispatch exists. "Integration test: a pre-boot dispatch is queued and delivered after `bootup-complete`" (line 355–356) presupposes dispatch queuing. If the thin-harness architecture has no dispatch (Finding 1), this test is meaningless. If only harness-lifecycle events are gated, the test should name those event types.
- **Evidence**: Line 355–356: "Integration test: a pre-boot dispatch is queued and delivered after bootup-complete." Line 42: "No dispatch logic."
- **Suggested fix**: Reword: "Integration test: a harness-originated lifecycle event (e.g., `compose-completed`) emitted while a role's `bootup_complete` is `False` is held and delivered to the event stream after that role emits `bootup-complete`." Or if the gate is removed (Finding 1 fix (a)), remove this test.

---

### Finding 16

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 141–142 and §10 (lines 714–736)
- **Severity**: warning
- **Issue**: The RESEARCH-harness-events.md's 8 open questions (lines 307–319) are never explicitly resolved or declared moot in CONTEXT.md. Some are moot under the thin-harness re-scope (questions 1–4 about dispatch mechanics), but others remain relevant: question 5 (singleton interaction — #8692 is a hard prereq, but the interaction analysis is missing), question 6 (bootstrap timeout during harness restart — unresolved), question 7 (`--target` flag semantics — unresolved and relevant to event_poll.py), question 8 (coordination with config flip — handled by sequencing but not explicitly closed). CONTEXT.md §10 lists 5 open questions, none of which address these.
- **Evidence**: CONTEXT.md line 141–142: "(This replaces the original RESEARCH framing where the harness pushes the next assigned-to.)" — closes only one RESEARCH question implicitly. RESEARCH-harness-events.md lines 307–319: 8 open questions. CONTEXT.md §10 lines 714–736: 5 open questions, all about implementation details, none about the RESEARCH's architectural concerns.
- **Suggested fix**: Add a §10 closing item: "RESEARCH open questions 1–4 and 7 are moot under the thin-harness no-dispatch architecture (the harness does not observe tracker state or emit `assigned-to`). Question 5 (singleton enforcement) is resolved by #8692 being a hard prerequisite. Question 6 (bootstrap timeout) and question 8 (config coordination) remain open — add to this section or lock: bootstrap watchdog = 60s, config coordination = per-role flip is gated on compose.py deploy."

---

### Finding 17

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 63–64 and 718–720
- **Severity**: warning
- **Issue**: Open question #1 asks "Confirm: no role-specific overrides ship in v1?" but the locked decision at line 63–64 already answers this: "(no overrides until empirical observation warrants)." The open question is redundant with the locked decision. If confirmation is still needed, the decision isn't actually locked.
- **Evidence**: Line 63–64: "Cool-down default = 30 minutes universal across roles, overridable per-role in config.md (no overrides until empirical observation warrants)." Line 718–720: "Confirm: no role-specific overrides ship in v1?"
- **Suggested fix**: Remove open question #1 — it's already decided. Or change the locked decision's parenthetical to "overrides TBD; see open question #1" if confirmation is genuinely pending.

---

### Finding 18

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 608–610 and 731–732
- **Severity**: warning
- **Issue**: The Phase 6 soak gate criterion is "tunable" and "not locked" (open question #5, line 731–732), but this creates a sequencing deadlock: if the soak period isn't defined before Phase 5 rollout completes, nobody knows when Phase 6 can start. The gate needs a concrete exit criterion — even if it's "PM judgment call" rather than a fixed duration.
- **Evidence**: Line 608–610: "event-driven operation has been observed stable for a tunable soak period." Line 731–732: "Soak period before Phase 6 — how long does event-driven operation need to be stable before #8698 / #8702 are picked up? Not locked."
- **Suggested fix**: Lock a minimum criterion. Options: "2 weeks of stable operation with zero event-processing incidents across all roles," "PM sign-off after all roles have operated in events mode for at least N full task cycles," or "PM judgment call at Phase 5 completion review." Even "PM judgment call" is a locked answer — it just delegates the timing to a human decision point.

---

### Finding 19

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: 70–73
- **Severity**: warning
- **Issue**: The DM comment re-read timing is ambiguous. "DM re-reads comments at task completion before next pickup" (line 72–73) means comments are checked only at the END of the PR-merge wait task. But the justification says "PR-merge wait can be long; comment-driven guidance like reassign / route back / file follow-up must be honored" — if the wait is long, re-reading only at the end means comment-driven reassignment could be delayed by hours. The atomicity rule (§2 line 57–59) says the task runs to completion with no mid-task action on events. Does DM have a sub-loop for periodic comment re-reading within the atomic wait task?
- **Evidence**: §3.7 line 70–73: "DM's task includes waiting for PR merges; comments may land during the wait. DM re-reads comments at task completion before next pickup." §2 line 57–59: "every task... runs to completion. Mid-task events are read and cursor-advanced but not acted on until the current task ends."
- **Suggested fix**: Clarify the expected behavior. If re-reading only at task end is intentional, document the tradeoff: "DM only acts on comment guidance at PR-merge completion; urgent reassignments must use status transitions (which generate events)." If periodic re-reading is intended, describe a sub-loop: "During PR-merge wait, DM periodically (configurable interval, default 5 minutes) re-reads issue comments without advancing the event cursor. If guidance is found, DM acts on it as a sub-action within the atomic wait task and then resumes waiting."