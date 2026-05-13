Now I have all the information needed to produce the comprehensive research document. Let me synthesize everything.

---

# FEAT-PM-7630-L1L4-REACTIONS Research — Mapping Event Reactions to the L1-L4 Layered Instruction Structure

## Summary

This research maps all 30+ current and proposed event types to the SquidSquad 4-layer instruction architecture (L1–L4). The PRD Section 3.2 (event catalog) defines 17 existing event types (12 emitted, 5 recognized) in `references/scripts/event_catalog.py` lines 26–117, plus ~13 proposed types from `CONTEXT.md` and the `GAP-REVIEW`. Currently all event reactions are in a single flat L1 sub-skill (`references/sub-skills/common/event-reactions.md`, 32 lines), which provides a 10-row generic table that says "do X regardless of your role." This violates the layered architecture and will break when the event-driven model replaces the cycle model — agents must react differently based on their role (L2), project context (L3), and human overrides (L4).

The recommendation is to distribute event reactions across all four layers: L1 defines universal mechanical reactions (what ALL agents do — e.g., stop-requested → checkpoint and exit), L2 defines role-specific reactions per role (what PM does vs dev vs QA vs DM for each event), L3 makes event reactions project-adaptable via `soul_adaptation.py` (e.g., quality bar for verification events, scan aggressiveness), and L4 enables human overrides in `config.md` (e.g., disable specific event types, change scan-idle-timeout, override stop behavior). The existing `event-reactions.md` becomes the L1 universal-only table and shrinks by ~60%. Each role's `instructions.md` gains an L2 event-reaction section. `soul_adaptation.py` gains event-reaction adaptation categories. `config.md` gains event-driven override fields.

**Primary risks**: (1) The event-driven architecture (#7630) is not yet implemented — the mapping is forward-looking and must be validated against actual Monitor tool / closure API behavior. (2) Role-specific reactions assume the current team composition (PM+QA+DM+devs), which is locked per #6261 but must hold. (3) L3 event adaptation is novel — `soul_adaptation.py` currently adapts personality only, not behavioral reactions.

## Vault Context

- **BRIEFING.md priorities**: #7630 is the active top priority — "next major architectural shift — all mechanical cycle steps move to harness." #6087 (L2 status line redesign) is related because status-line sub-skills will need L2 event reaction integration. #5783 (L3 bug investigation boundary) is relevant for how L3 adaptations shape dev-vs-PM event reactions.
- **Related decisions**: [[decision-cycle-runner-architecture]] — The #2057 mechanical/creative split established the pattern of separating deterministic from LLM work. #7630 extends this: reactions are now split across L1 (deterministic, harness-handled) and L2/L3/L4 (creative, agent-handled). [[decision-sub-skill-architecture]] — constrains how sub-skills are composed: L1 content comes from `references/roles/instructions.md` + `includes.yml` manifests, L2 from `references/roles/{role}/instructions.md`, L3 from domain variants, L4 from `.squidsquad/project/`. [[decision-clone-isolation-architecture]] — clone agents run as siblings, which affects event bus port discovery and thus which agents receive which events. [[decision-pid-primary-liveness]] — OS-level truth preferred over file-based health signals; this shapes agent-health event reactions.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — directly applicable: any event reaction with >2 conditional branches should be a script, not prose. The current event-reactions.md is already pushing this boundary. [[pattern-windows-utf8-subprocess]] — Windows subprocess handling matters for event bus reader in clones.
- **Human preferences**: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" — this is the core driver. L1 mechanical reactions must be harness code, not agent prose instructions. "Systems should self-heal: detect stuck states → unstick immediately" — shapes how L2 PM reactions to agent-health and pipeline-stalled events must work. "Prefers direct/mechanical checks over indirect state files" — event reactions should use direct checks where possible. Context pressure threshold: 70%.
- **Related learnings**: [[learning-atomic-migration-strategy]] — any splitting of event-reactions across L1-L4 must be atomic: all 4 roles' instructions.md, all 4 includes.yml, and the event-reactions.md sub-skill must change in one compose deploy-all. [[learning-commit-code-state-exclusion]] — `.squidsquad/` files that are code (like statusline.sh) get excluded from commits; event-reaction scripts that live under `.squidsquad/` need special handling.

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/common/event-reactions.md` — REWRITTEN: stripped to L1 universal reactions only (mechanical, informational events)
  - `references/sub-skills/common/event-driven-workflow.md` — NEW: replaces cycle-runner.md with event handler descriptions (the "when woken by event X, do Y" table)
  - `references/roles/pm/instructions.md` — ADD L2 event-reaction section for PM-specific event handling
  - `references/roles/dev/instructions.md` — ADD L2 event-reaction section for dev-specific event handling
  - `references/roles/qa/instructions.md` — ADD L2 event-reaction section for QA-specific event handling
  - `references/roles/dm/instructions.md` — ADD L2 event-reaction section for DM-specific event handling
  - `references/roles/pm/includes.yml` — remove `common/event-reactions`, add `roles/pm/event-reactions`
  - `references/roles/dev/includes.yml` — remove `common/event-reactions`, add `roles/dev/event-reactions`
  - `references/roles/qa/includes.yml` — remove `common/event-reactions`, add `roles/qa/event-reactions`
  - `references/roles/dm/includes.yml` — remove `common/event-reactions`, add `roles/dm/event-reactions`
  - `references/sub-skills/roles/pm/event-reactions.md` — NEW: PM-specific event reaction guidance
  - `references/sub-skills/roles/dev/event-reactions.md` — NEW: dev-specific event reaction guidance
  - `references/sub-skills/roles/qa/event-reactions.md` — NEW: QA-specific event reaction guidance
  - `references/sub-skills/roles/dm/event-reactions.md` — NEW: DM-specific event reaction guidance
  - `references/scripts/soul_adaptation.py` — EXTEND: add event-reaction adaptation categories (lines 42–48, `CATEGORIES` list)
  - `.squidsquad/vault/areas/role-adaptations.md` — NEW entries for event-reaction adaptations (file doesn't exist yet; `_ensure_adaptations_file()` at line 60 will create it)
  - `.squidsquad/config.md` — ADD event-driven override fields: `event-driven`, `scan-idle-timeout`, `wake-mechanism`
  - `references/roles/instructions.md` (L1 base) — UPDATE: add "Event Model" section explaining the universal event contract
  - `references/scripts/event_catalog.py` — ADD event-reaction tier field to each event type entry
  - `.squidsquad/vault/areas/human-profile.md` — ADD event-reaction preferences section (L4)

- **Behavior changes**:
  1. Event reactions are no longer a flat 10-row table — agents see only their role's reactions plus the L1 universal table
  2. Mechanical events (git-pull, git-push, git-commit, branch-checkout, pr-create, request-merge, cycle-start, cycle-end) move entirely to L1 informational — agents note them but take no creative action
  3. Role-specific events (verification-failed, verification-passed, scan-due, human-input-received) appear ONLY in the relevant role's L2 instructions
  4. L3 adaptations can tune reaction behavior (e.g., "quality-preference: exhaustive" → QA runs extra verification on verification-failed events)
  5. L4 overrides in config.md can disable event types or change reaction parameters

- **Dependencies**: compose.py (already supports manifest-driven include resolution at lines 209–277), soul_adaptation.py (already renders adaptations into SOUL.md), config.py (already reads config.md fields), event_catalog.py (source of truth for event type definitions).

## Side Effects

- **Risk 1**: L2 event reactions assume stable team composition — Severity: M — If the fixed team architecture (#6261) changes (e.g., adding a designer role), new L2 event-reaction files must be created for the new role and all existing L2 files must be reviewed for cross-role references. Mitigation: document the assumption; compose.py `_assemble_claude()` at line 280 already handles missing base instructions gracefully.

- **Risk 2**: Event-reaction files contain bash commands that reference cycle scripts — Severity: H — Many L2 reactions today involve `tracker.py transition`, `git_ops.py task-begin`, etc. In the event-driven model, these move to the closure API. If L2 event-reaction files are written before the closure API exists, they'll reference the wrong mechanism. Mitigation: write L2 event reactions in two modes — "cycle model" (current, gated by `event-driven: no`) and "event model" (future, gated by `event-driven: yes`). Use `{{if event-driven}}` compose directives or separate sub-skill variants.

- **Risk 3**: compose.py's manifest resolution may silently skip new L2 includes — Severity: L — At line 246, if an `{{include:}}` directive in the instructions.md references a path not in the manifest, it's silently skipped. If the new L2 event-reactions are added to instructions.md but forgotten in includes.yml, agents get zero event-reaction guidance. Mitigation: add validation that `event-reactions` is always included for all roles; compose.py could warn on roles missing this include.

## Edge Cases

- **Compose-completed race with stale templates**: If an agent reads its CLAUDE.md mid-cycle while compose is deploying (RACE-2 from GAP-REVIEW), the agent could have mixed old-L1/new-L2 event reactions. Mitigation: atomic compose writes (`.tmp` → `mv`) already in place; agent re-reads CLAUDE.md on each event wake (not mid-cycle).

- **Clone agent doesn't receive role-specific events**: Event bus reader for clone agents may silently return `[]` (GAP-RACE-6). If L2 event reactions are built assuming agents always see events, clone agents will never trigger them. Mitigation: L1 universal event-reactions.md must include: "If recent_events is empty and you expected events, your event bus discovery may be broken — file a bug."

- **L3 adaptation conflicts with L4 human override**: If soul_adaptation.py sets `quality-preference: exhaustive` (extra verification on all events) but human-profile.md says `quality-preference: minimal` (ship fast, test later), which wins? Mitigation: L4 always wins over L3. soul_adaptation.py's `render_soul()` at line 190 should check for L4 override fields before rendering.

- **Event type not in any L2 file**: If a new event type is added to event_catalog.py but no L2 reaction is written, agents see the event with no guidance. Mitigation: L1 universal table includes a catch-all: "Unknown/unhandled event types: log the event ID, note it in working state, proceed."

- **PM and QA both react to same event (duplicate work)**: For verification-failed, both PM (pipeline sentinel) and QA (verification) might act. Mitigation: L2 files must include clear "who owns this" rules. PM owns pipeline sentinel reactions (detects stalls). QA owns verification reactions (runs tests). If overlap, PM must check if QA has already acted before acting.

## Integration Risks

- **compose.py assemble order**: L1 → L2 → L3 → L4 layers are assembled in `_assemble_claude()` at lines 291–341. L4 project sub-skills are appended LAST (lines 319–339), which means they can override earlier content. This is correct for L4 overrides but means L2 event-reaction files must not repeat L1 universal content (compose concatenates, doesn't deduplicate).

- **soul_adaptation.py doesn't currently handle event reactions**: The 5 categories (deliverable-type, tech-stack, domain-vocabulary, quality-preference, user-persona) at line 42–48 don't include event-reaction tuning. Extending this requires adding categories like `event-sensitivity` (how aggressively to react to events), `reaction-latency` (how quickly to respond), and `scan-priority` (which events trigger scans). This is a new capability, not a modification.

- **config.md doesn't have event-driven fields yet**: The event-driven config fields (`event-driven: yes/no`, `scan-idle-timeout: 10`, `wake-mechanism: monitor|spawn`) are defined in CONTEXT.md but not in `config.py` FIELD_MAP (lines 38–95). They must be added before L4 overrides can reference them.

- **Status bar and cycle timer**: statusline.sh lines 88–119 use `current-state` file mtime for cycle timer. When cycles are eliminated, the status bar must switch to event-based display. L2 event reactions include status bar writes — if the bar format changes, all L2 files must update.

## Upgrade & Migration

- **New config values**:
  - `event-driven: no` — default `no` (gates all event-driven behavior)
  - `scan-idle-timeout: 10` — default `10` minutes
  - `wake-mechanism: monitor` — default `monitor` (future: `spawn`)
  - `event-reaction-tiers: all` — new field: controls which L1-L4 tiers are active (default `all`; could be `l1-only` for debugging)

- **New files**:
  - `references/sub-skills/roles/pm/event-reactions.md`
  - `references/sub-skills/roles/dev/event-reactions.md`
  - `references/sub-skills/roles/qa/event-reactions.md`
  - `references/sub-skills/roles/dm/event-reactions.md`
  - `references/sub-skills/common/event-driven-workflow.md` (only added when event-driven mode activates)

- **Template changes**: 4 includes.yml files remove `common/event-reactions` and add their role-specific `roles/{role}/event-reactions`. 4 instructions.md files gain an L2 event-reaction section (or rely on the sub-skill include). L1 base `references/roles/instructions.md` gains a short "Event Model" section. `common/event-reactions.md` is rewritten to L1-only content.

- **Upgrade steps**: 1) Write role-specific event-reaction sub-skills. 2) Update all includes.yml manifests. 3) Update instructions.md files with event-model prose. 4) Run `compose.py deploy-all` to regenerate all CLAUDE.md files. 5) Verify each role's composed CLAUDE.md contains both L1 universal reactions and their L2 role-specific reactions. 6) Optionally: add L3 adaptations via `soul_adaptation.py add <role> --category event-sensitivity --signal "..."`. 7) Optionally: set L4 overrides in `config.md`.

- **Graceful degradation**: When `event-driven: no` (default), agents continue using the cycle model. The old flat `event-reactions.md` content is preserved in the L1 file and the role-specific L2 files are NOT included (their includes.yml entries are gated). When `event-driven: yes`, the L2 files are included and the L1 file is the new slim version. This requires compose.py to support conditional includes (not currently implemented — would need a `{{if config:event-driven}}` directive or separate manifests for each mode).

## Open Questions

- **Q1**: How should compose.py gate which event-reaction files are included based on `event-driven` config? — **Why**: The L2 role-specific event-reaction files are only meaningful in event-driven mode. In cycle mode, the old flat event-reactions.md suffices. Without gating, agents in cycle mode get confusing "when you are woken by event X" instructions. The current compose.py has no conditional include mechanism.

- **Q2**: Should L3 event-reaction adaptations live in SOUL.md (personality) or in a separate event-reaction adaptation mechanism? — **Why**: soul_adaptation.py renders into SOUL.md which is about personality/character, not behavioral rules. Mixing "be more aggressive in QA verification" with "you are a meticulous tester" is blurry. A separate L3 mechanism for event-reaction tuning might be cleaner, but adds complexity.

- **Q3**: For events where the reaction is ONLY mechanical (harness handles, no agent reaction), should they even appear in agent templates? — **Why**: The current event-reactions.md lists mechanical events like `pr-merged` and `compose-completed` with "read for awareness" guidance. If harness handles these entirely, they could be filtered out before reaching agents, saving context. But agents might need awareness for coordination. Where to draw the line?

- **Q4**: What is the compose order when both L2 event-reactions sub-skill AND inline L2 event-reaction prose exist in instructions.md? — **Why**: The current instructions.md files contain inline prose (the Ralph Loop steps). If role-specific event reactions are both a sub-skill include and inline in instructions.md, compose will duplicate content. Must decide: either sub-skill only, or inline only, not both.

## Recommendation

**Feasible with caveats.** The mapping of event types to L1-L4 layers is clear and well-defined. The main caveats are:

1. **Compose gating is the blocker**: The current `compose.py` has no conditional include mechanism. Without it, you cannot ship L2 event-reaction files that work in both cycle mode and event-driven mode. Either: (a) add `{{if config:event-driven}}` directives to compose.py (2-3 days of work), or (b) accept that L2 event-reaction files ship only when event-driven mode is fully delivered, keeping the flat `event-reactions.md` as a transitional artifact.

2. **L3 event adaptation is novel territory**: soul_adaptation.py was designed for personality adaptation, not behavioral reaction tuning. Extending it is feasible (add 2-3 new categories) but should be scoped carefully to avoid confusing personality signals with behavioral rules.

3. **Start with L1+L2 only, defer L3+L4**: The concrete value is in splitting the flat event-reactions.md into L1 (universal) and L2 (role-specific). This can be done immediately, before #7630 event-driven architecture is complete, because agents already receive `recent_events` via `cycle-input.json`. L3 and L4 are lower-priority enhancements.

---

## Complete Event Type → Layer Mapping Table

### Legend
- **L1**: Universal — all roles do the same thing. Sub-skill: `common/event-reactions.md`
- **L2**: Role-specific — each role has unique reaction. Sub-skills: `roles/{role}/event-reactions.md`
- **L3**: Project-adaptable — tuned via `soul_adaptation.py` categories
- **L4**: Human-overridable — configurable via `config.md` or `human-profile.md`
- **Mech**: Mechanical only — harness handles entirely, agent sees for awareness only
- **✗**: Not applicable at this layer
- **✓**: Applicable at this layer

### A. CURRENT EMITTED Events (event_catalog.py lines 26–87)

| # | Event Type | Source | L1 (Universal) | L2 (Role-Specific) | L3 Adaptable? | L4 Overridable? | Mech? |
|---|-----------|--------|----------------|---------------------|---------------|-----------------|-------|
| 1 | `cycle-start` | cycle_pre.py:26 | Awareness only — "another agent started a cycle." No action needed. | ✗ (all roles same) | ✗ | ✗ | **Mech** |
| 2 | `cycle-end` | cycle_post.py:26 | Awareness only — "another agent completed a cycle." No action needed. | ✗ (all roles same) | ✗ | ✗ | **Mech** |
| 3 | `git-pull` | git_ops.py:37 | Awareness only — "code was pulled." No action needed. | ✗ | ✗ | ✗ | **Mech** |
| 4 | `git-push` | git_ops.py:42 | Awareness only — "code was pushed." No action needed. | ✗ | ✗ | ✗ | **Mech** |
| 5 | `git-commit` | git_ops.py:47 | Awareness only — "commit created." No action needed. | ✗ | ✗ | ✗ | **Mech** |
| 6 | `status-transition` | tracker.py:53 | **Read the transition**: Check if it affects your current work or queue. | **PM**: Check pipeline impact (stall detection, unblock detection). **Dev**: If your task's status changed, adapt. **QA**: If item moved to pending-test, queue verification. **DM**: If item moved to pending-ship, queue delivery. | ✓ (quality-preference: how aggressively to verify transitions) | ✓ (disable specific transition notifications) | — |
| 7 | `tracker-comment` | tracker.py:58 | **Read the comment**: Check if it mentions your task or role. | **PM**: Scan for human input in comments. **Dev**: If comment is on your task, read and respond. **QA**: If comment is verification feedback, incorporate. **DM**: If comment is delivery notes, apply. | ✓ (domain-vocabulary: keywords that trigger priority attention) | ✓ (mute comments from specific roles) | — |
| 8 | `branch-checkout` | git_ops.py:62 | Awareness only — "branch was checked out." | ✗ | ✗ | ✗ | **Mech** |
| 9 | `pr-create` | git_ops.py:67 | Awareness only — "PR was created." | ✗ | ✗ | ✗ | **Mech** |
| 10 | `pr-merge` | git_ops.py:72 | **DEPRECATED** — use `pr-merged` from harness. If seen, treat as `pr-merged`. | ✗ (same as pr-merged) | ✗ | ✗ | **Mech** |
| 11 | `pr-merged` | harness.py:77 | **Pull latest on next task boundary**. Check if merged code affects your work. | **PM**: Run pipeline sentinel — check if PR close invalidates any state. **Dev**: Pull main, check if merged code conflicts with in-progress work. **QA**: Update verification queue — merged code may need retesting. **DM**: Check if merged PR has pending-ship items ready for delivery. | ✓ (tech-stack: merge strategies that need special handling) | ✓ (ignore merges from specific branches/roles) | — |
| 12 | `compose-completed` | harness.py:82 | **Your templates may have changed**. Harness reboots affected agents automatically. Read your CLAUDE.md on next cycle to see changes. | **All roles**: Re-read CLAUDE.md at next cycle start. **PM**: Verify compose affected all intended roles. **DM**: Note if compose changed user-facing docs. | ✗ | ✓ (suppress compose notifications) | — |

### B. CURRENT RECOGNIZED Events (event_catalog.py lines 91–117)

| # | Event Type | Planned Source | L1 (Universal) | L2 (Role-Specific) | L3 Adaptable? | L4 Overridable? | Mech? |
|---|-----------|---------------|----------------|---------------------|---------------|-----------------|-------|
| 13 | `verification-failed` | qa/pm verification:93 | **If your task**: Read the failure feedback, fix all gaps, re-submit. | **Dev**: Read QA/PM feedback. Fix the issues. Transition back to in-progress → pending-test after fixing. **PM**: Route the failure to the correct dev. Note in pipeline sentinel. **QA**: Record the failure in QA log. Track re-submission. **DM**: Await re-verification — do not ship. | ✓ (quality-preference: threshold for auto-reject vs. human review) | ✓ (escalate specific failures to human) | — |
| 14 | `verification-passed` | qa/pm verification:97 | **If your task**: Await shipping — DM handles the rest. | **Dev**: Task complete — clear working state. Move to next task. **PM**: Update pipeline sentinel. Route to DM. **QA**: Record pass in QA log. **DM**: Pick up for delivery packaging. | ✓ (deliverable-type: what delivery steps apply) | ✓ (hold shipment pending human review) | — |
| 15 | `agent-health` | harness.py health poller:102 | **Note if it blocks your work**: If an agent you depend on is dead/stalled, adjust your queue. | **PM**: Investigate unhealthy agents. Restart if needed. File bug if persistent. Reassign stalled agent's tasks. **Dev**: If PM is unhealthy, continue working from existing queue. If QA is unhealthy, self-verify more carefully. **QA**: If dev agents are unhealthy, note in health log. **DM**: If QA is unhealthy, defer shipments. | ✓ (quality-preference: tolerance for agent downtime before escalating) | ✓ (set health check interval, disable auto-restart) | — |
| 16 | `phase-change` | harness.py or pm:107 | **Check if it unblocks your queue**: A task moving phases may release work. | **PM**: Primary handler — track lifecycle phases. Detect stuck phases. **Dev**: If phase change affects your task, adapt. **QA**: If phase change triggers verification, queue it. **DM**: If phase change triggers delivery, prepare. | ✗ | ✓ (disable phase-change notifications) | — |
| 17 | `request-merge` | harness.py:113 | **Audit trail only** — no action needed. | ✗ | ✗ | ✗ | **Mech** |

### C. PROPOSED NEW Events (from GAP-REVIEW lines 181–208, CONTEXT.md, TEST-PLAN.md)

| # | Event Type | Proposed Source | L1 (Universal) | L2 (Role-Specific) | L3 Adaptable? | L4 Overridable? | Mech? |
|---|-----------|----------------|----------------|---------------------|---------------|-----------------|-------|
| 18 | `work-available` | harness (new) | **Wake signal**: Harness has work for you. Read the event payload for work context. Begin creative work. | **All roles**: This is THE activation event. Each role reads the work-context payload and does their role-specific creative work. | ✓ (domain-vocabulary: what "work" means per project) | ✓ (disable work-available for specific roles — e.g., pause dev) | — |
| 19 | `work-started` | harness (new) | Awareness only — "agent began work." No action needed. | ✗ | ✗ | ✗ | **Mech** |
| 20 | `work-completed` | harness (new) | Awareness only — "agent completed work." No action needed. | ✗ | ✗ | ✗ | **Mech** |
| 21 | `agent-idle` | harness (new) | Awareness only — "agent has no pending work." | **PM**: Track idle agents. If all idle for too long, investigate stall. | ✓ (quality-preference: idle timeout before escalation) | ✓ (set idle timeout per role) | **Mech** |
| 22 | `stop-requested` | harness (Locked Decision #2) | **UNIVERSAL STOP**: (1) Checkpoint working-state.md immediately. (2) If mid-event, post partial closure or note interruption. (3) Exit cleanly. **This is the highest-priority event** — all other work yields to it. | ✗ (ALL roles do exactly the same thing) | ✗ | ✓ (grace period before forced kill; disable terminal close) | — |
| 23 | `agent-stopping` | harness (new) | Awareness only — "agent is shutting down." | **PM**: Note for pipeline continuity. Reassign in-flight tasks. | ✗ | ✗ | **Mech** |
| 24 | `agent-stopped` | harness (new) | Awareness only — "agent exited." | **PM**: Verify clean exit. Trigger restart if needed. **QA**: Note for health log. | ✗ | ✗ | **Mech** |
| 25 | `scan-due` | harness (Locked Decision #5) | **PM ONLY**: Run improvement scan on targets in event payload. Write findings to cycle-output.json. Close event via API. **All other roles**: This event is not for you — ignore. | **PM**: Primary handler — run improvement scan, file findings. **Dev/QA/DM**: Not for you. | ✓ (quality-preference: scan depth and aggressiveness) | ✓ (scan-idle-timeout duration; disable scan-due entirely) | — |
| 26 | `scan-completed` | harness (new) | Awareness only — "scan finished." Read findings if they reference your domain. | **PM**: Review scan results. Route findings to appropriate agents. **Dev**: Check if findings reference your code. **QA**: Check for test-related findings. **DM**: Check for doc/delivery findings. | ✗ | ✓ (suppress scan-completed notifications) | **Mech** |
| 27 | `event-timeout` | harness (new) | Awareness only — "an event timed out." Harness handles recovery. | **PM**: Investigate if timeout pattern indicates systemic issue. File bug if frequent. | ✗ | ✓ (set timeout durations per event type) | **Mech** |
| 28 | `event-reemitted` | harness (new) | **Duplicate possible**: Harness re-emitted an event after crash. Check if you already processed the original. If yes, skip (idempotent). If no, process normally. | ✗ (all roles check for duplicates) | ✗ | ✗ | **Mech** |
| 29 | `work-failed` | harness (new) | Awareness only — "agent failed to process event." Harness handles recovery. | **PM**: Investigate failure. Reassign work if needed. **Dev**: If your failure, check why. | ✓ (quality-preference: auto-retry vs. human escalation) | ✓ (max retries per event) | **Mech** |
| 30 | `human-input-received` | harness (new) | Awareness only — note that human provided input. | **PM**: Primary handler — read human input, process according to checkin protocol. **Dev/QA/DM**: Check if input references your work. | ✓ (domain-vocabulary: keywords that signal priority human input) | ✓ (route human input to specific roles) | — |
| 31 | `vault-reflect` | harness (new — out of scope per CONTEXT.md:98) | **Read vault for changes**: Harness detected vault state change. Check BRIEFING.md and recent decisions. | **PM**: Run vault reflection pipeline. **Dev**: Check for new decisions affecting your work. **QA**: Check for new patterns affecting verification. **DM**: Check for new learnings affecting delivery. | ✓ (quality-preference: vault reflection depth) | ✓ (disable vault-reflect; set reflection interval) | — |
| 32 | `pipeline-stalled` | harness (new — from human-profile.md:36) | Awareness only — "pipeline may be stuck." | **PM**: Primary handler — diagnose and unstick. File root-cause bug. **Dev/QA/DM**: Check if stall affects your work. | ✓ (quality-preference: auto-unstick aggressiveness) | ✓ (stall detection thresholds per status) | — |
| 33 | `templates-updated` | harness (new — from RACE-2 fix) | **Your templates changed**: Harness has updated CLAUDE.md due to compose. Re-read your CLAUDE.md at next event boundary. | **All roles**: Re-read CLAUDE.md. **PM**: Verify compose deployed to all roles. | ✗ | ✓ (suppress template-updated notifications) | **Mech** |

---

## Proposed Content Structure

### L1 — `references/sub-skills/common/event-reactions.md` (REWRITTEN)

**What stays (universal mechanical events)**:
- Definition of what `recent_events` and `mechanical_reactions` are (lines 1–5, preserved)
- The "Mechanical vs Creative" section (lines 23–26, preserved)
- The "Rules" section (lines 28–31, preserved)
- A table covering ONLY universal events: `cycle-start`, `cycle-end`, `git-pull`, `git-push`, `git-commit`, `branch-checkout`, `pr-create`, `request-merge`, `work-started`, `work-completed`, `agent-idle`, `agent-stopping`, `agent-stopped`, `event-timeout`, `event-reemitted`, `work-failed`, `templates-updated`
- The `stop-requested` universal reaction (checkpoint → exit)
- The `event-reemitted` idempotency rule (check if already processed)

**What moves to L2**:
- All role-specific event reactions: `status-transition`, `tracker-comment`, `pr-merged`, `verification-failed`, `verification-passed`, `agent-health`, `phase-change`, `scan-due`, `human-input-received`, `vault-reflect`, `pipeline-stalled`
- The current table's "What each event type means for you" column — split per role

**Estimated size**: ~25 lines (down from current 32, but much more focused)

### L2 — `references/sub-skills/roles/{role}/event-reactions.md` (NEW × 4)

Each file contains a role-specific table:

**`roles/pm/event-reactions.md`** — PM reactions:
- `status-transition` → pipeline sentinel check, stall detection
- `tracker-comment` → scan for human input, route to correct agent
- `pr-merged` → check for merge conflicts, update pipeline state
- `verification-failed` → route failure to correct dev, note in sentinel
- `verification-passed` → update sentinel, route to DM
- `agent-health` → investigate unhealthy agents, restart if needed, reassign tasks
- `phase-change` → track lifecycle, detect stuck phases
- `scan-due` → run improvement scan, file findings
- `human-input-received` → process according to checkin protocol
- `vault-reflect` → run vault reflection pipeline
- `pipeline-stalled` → diagnose, unstick, file root-cause bug
- `compose-completed` → verify deploy reached all roles

**`roles/dev/event-reactions.md`** — Dev reactions:
- `status-transition` → check if own task status changed
- `tracker-comment` → read if on own task
- `pr-merged` → pull latest, check for conflicts with in-progress work
- `verification-failed` → read feedback, fix gaps, re-submit
- `verification-passed` → clear working state, move to next task
- `agent-health` → adapt if dependent agents are unhealthy
- `vault-reflect` → check for new decisions affecting implementation

**`roles/qa/event-reactions.md`** — QA reactions:
- `status-transition` → if item moves to pending-test, queue verification
- `tracker-comment` → read verification feedback
- `pr-merged` → update verification queue (merged code may need retesting)
- `verification-failed` → record in QA log, track re-submission
- `verification-passed` → record pass, hand off to DM
- `agent-health` → note in health log
- `phase-change` → if triggers verification, queue it
- `vault-reflect` → check for new patterns affecting verification

**`roles/dm/event-reactions.md`** — DM reactions:
- `status-transition` → if item moves to pending-ship, queue delivery
- `tracker-comment` → read delivery notes, apply to delivery package
- `pr-merged` → check if merged PR has pending-ship items
- `verification-passed` → pick up for delivery packaging
- `agent-health` → defer shipments if QA unhealthy
- `compose-completed` → check if compose changed user-facing docs
- `vault-reflect` → check for new learnings affecting delivery

### L3 — `soul_adaptation.py` EXTENSIONS

**New adaptation categories** (add to `CATEGORIES` list at line 42):

```python
CATEGORIES = [
    "deliverable-type",
    "tech-stack",
    "domain-vocabulary",
    "quality-preference",
    "user-persona",
    # New event-reaction categories:
    "event-sensitivity",    # How aggressively to react to events (reactive ↔ proactive)
    "reaction-latency",     # How quickly to respond to time-sensitive events
    "scan-priority",        # Which event types trigger improvement scans
]
```

**How it works**: PM writes adaptation entries to `role-adaptations.md`:
```
### pm
- [2026-05-20] **event-sensitivity**: Pipeline-stalled events trigger immediate investigation within 5 minutes (from #7630)
- [2026-05-20] **reaction-latency**: Verification-failed events should be re-routed to dev within 1 cycle (from #7630)
```

These are rendered into SOUL.md under `## Project Adaptation` and influence how agents interpret L2 event reactions.

### L4 — Human Overrides

**In `config.md`** (new fields):
```markdown
## Event-Driven (L4 overrides)
- **Event-Driven Mode**: yes
- **Scan Idle Timeout**: 10
- **Wake Mechanism**: monitor
- **Muted Event Types**: (none)
- **Stop Grace Period**: 30
- **Max Event Retries**: 3
```

**In `human-profile.md`** (new section):
```markdown
## Event Reaction Preferences
- **Escalation threshold**: Escalate unhandled events to human after 2 consecutive cycles
- **Auto-unstick policy**: Auto-unstick pipeline stalls; file bug after 3 auto-unsticks on same item
- **Notification preference**: Notify human on: verification-failed (severity:high), agent-health (status:dead), pipeline-stalled
```

---

## Sub-Skills and Instructions Needing Changes

### Files that MUST change (atomic deploy):

| File | Change |
|------|--------|
| `references/sub-skills/common/event-reactions.md` | Rewrite to L1 universal-only (~25 lines) |
| `references/sub-skills/roles/pm/event-reactions.md` | **NEW** — PM-specific event reactions |
| `references/sub-skills/roles/dev/event-reactions.md` | **NEW** — Dev-specific event reactions |
| `references/sub-skills/roles/qa/event-reactions.md` | **NEW** — QA-specific event reactions |
| `references/sub-skills/roles/dm/event-reactions.md` | **NEW** — DM-specific event reactions |
| `references/roles/pm/includes.yml` | Replace `common/event-reactions` with `roles/pm/event-reactions` |
| `references/roles/dev/includes.yml` | Replace `common/event-reactions` with `roles/dev/event-reactions` |
| `references/roles/qa/includes.yml` | Replace `common/event-reactions` with `roles/qa/event-reactions` |
| `references/roles/dm/includes.yml` | Replace `common/event-reactions` with `roles/dm/event-reactions` |

### Files that SHOULD change:

| File | Change |
|------|--------|
| `references/roles/instructions.md` (L1 base) | Add "Event Model" section explaining universal event contract |
| `references/roles/pm/instructions.md` | Add inline event-model orientation prose (or rely on sub-skill include only) |
| `references/roles/dev/instructions.md` | Same |
| `references/roles/qa/instructions.md` | Same |
| `references/roles/dm/instructions.md` | Same |

### Files that MAY change (deferred):

| File | Change |
|------|--------|
| `references/scripts/soul_adaptation.py` | Add event-reaction adaptation categories (lines 42–48) |
| `.squidsquad/vault/areas/role-adaptations.md` | Add event-reaction adaptation entries |
| `.squidsquad/config.md` | Add event-driven L4 override fields |
| `.squidsquad/vault/areas/human-profile.md` | Add event-reaction preferences section |
| `references/scripts/event_catalog.py` | Add `reaction_tier` field to each event type entry (metadata only) |

## Mechanical-Only vs Creative Events

### Events where reaction is ONLY mechanical (harness handles, agent needs NO prose guidance):
1. `cycle-start` — informational
2. `cycle-end` — informational
3. `git-pull` — informational
4. `git-push` — informational
5. `git-commit` — informational
6. `branch-checkout` — informational
7. `pr-create` — informational
8. `pr-merge` — DEPRECATED, informational
9. `request-merge` — informational
10. `work-started` — informational
11. `work-completed` — informational
12. `agent-idle` — informational (but PM may want to know)
13. `agent-stopping` — informational
14. `agent-stopped` — informational
15. `event-timeout` — harness handles recovery
16. `event-reemitted` — harness handles re-emission (agent just checks idempotency)
17. `work-failed` — harness handles recovery
18. `templates-updated` — harness reboots agent

**Recommendation**: These 18 event types should NOT appear in agent templates at all. They should be filtered out by the harness before delivering `recent_events` to agents. The L1 `event-reactions.md` should say: "You will only see events that require your judgment. Mechanical events (git operations, cycle bookkeeping, work lifecycle) are filtered by the harness. If you see an event, it needs your creative attention." This saves context and prevents agents from "noting" mechanical events that don't affect them.

### Events requiring creative agent judgment (must stay in templates):
1. `status-transition` — requires context: "does this affect MY work?"
2. `tracker-comment` — requires reading and understanding comment content
3. `pr-merged` — requires context: "does this merged code conflict with my work?"
4. `verification-failed` — requires reading feedback and fixing specific gaps
5. `verification-passed` — requires knowing what to do next
6. `agent-health` — requires deciding whether to escalate
7. `phase-change` — requires understanding pipeline impact
8. `compose-completed` — requires re-reading CLAUDE.md
9. `scan-due` — requires running improvement scan with judgment
10. `human-input-received` — requires reading and processing human input
11. `vault-reflect` — requires reading vault and applying findings
12. `pipeline-stalled` — requires diagnosing and un-sticking
13. `stop-requested` — requires checkpointing and clean exit
14. `work-available` — requires doing creative work

These 14 event types are the ones that need L2 role-specific reactions and L3/L4 adaptation.

---

## Vault Candidates

- **Type**: decision — Event reactions distributed across L1-L4 layers instead of flat single-skill — **Why**: Establishes a new architectural pattern for how agent instructions handle event-driven behavior. The L1 universal + L2 role-specific + L3 adaptable + L4 overridable split mirrors the existing compose assembly order and should be the default for any future cross-cutting behavior.
- **Type**: pattern — Mechanical-only events should be filtered by harness, not listed in agent templates — **Why**: 18 of 32 event types are purely mechanical. Listing them in agent templates wastes context and invites LLMs to "note" or "act on" events that need no action. The pattern: harness filters events before delivering `recent_events`; agents only see events requiring judgment.
- **Type**: learning — compose.py has no conditional include mechanism, which forces all-or-nothing template changes — **Why**: The event-driven architecture needs different sub-skills depending on `event-driven: yes/no` config. Without `{{if config:...}}` directives, you must either ship separate manifests or ship event-driven content prematurely. This is a known constraint that affects all future config-gated template changes.
- **Type**: decision — L2 event-reaction sub-skills replace inline event-reaction prose in instructions.md — **Why**: The current instructions.md files contain ~200+ lines of cycle prose that will be replaced by event-reaction prose. Whether this goes in sub-skills (composed via includes.yml) or inline in instructions.md (direct edit) affects maintainability, variant inheritance, and compose complexity. Sub-skills are recommended because they work with existing variant inheritance (L3 domain variants).
- **Type**: learning — soul_adaptation.py was designed for personality, not behavior — extending it to event reactions risks category confusion — **Why**: The 5 current categories (deliverable-type, tech-stack, domain-vocabulary, quality-preference, user-persona) shape agent personality/identity. Adding event-reaction tuning (event-sensitivity, reaction-latency, scan-priority) is a different concern — behavioral rules, not personality. If these get mixed in SOUL.md, agents may interpret behavioral rules as personality traits, causing unpredictable behavior. A separate L3 mechanism for behavior tuning may be warranted.