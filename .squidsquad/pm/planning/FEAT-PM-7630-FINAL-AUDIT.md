Now I have all the information needed. Let me compile the final audit.

---

# FEAT-PM-7630-FINAL-AUDIT Research — Cross-Document Consistency Audit

## Summary

I audited all three documents — **FEAT-PM-7630-PRD.md** (`.squidsquad/pm/planning/FEAT-PM-7630-PRD.md`), **FEAT-PM-7630-CONTEXT.md** (`.squidsquad/pm/planning/FEAT-PM-7630-CONTEXT.md`), and **FEAT-PM-7630-TEST-PLAN.md** (`.squidsquad/pm/planning/FEAT-PM-7630-TEST-PLAN.md`) — against the 10 specified consistency points plus cross-cutting issues. The PRD is out of sync with CONTEXT.md and TEST-PLAN.md on three major points: the config gate, backward compatibility, and who owns git push. The TEST-PLAN.md has a critical operational issue: 6 comprehension questions reference `event-reactions.md` as a source file, but the PRD and CONTEXT.md declare `event-reactions.md` **deleted**. The PRD itself is internally contradictory on `event-driven` as a config field (listed in Upgrade section but absent from FIELD_MAP and config template). The remaining 7 points are consistent across all three documents.

**Recommendation**: The PRD must be updated to match CONTEXT.md (which reflects Locked Decisions from human). The TEST-PLAN.md must fix CQ file references. The PRD's internal contradiction on `event-driven` config field must be resolved in favor of CONTEXT.md (no config gate).

## Vault Context

- **BRIEFING.md priorities**: #7630 EPIC explicitly listed as active priority. "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose — drives #7630." "All mechanical cycle steps move to harness."
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 split was intermediate step toward #7630. Vault confirms #7630 is the successor, moving all mechanical operations into the harness. The PRD references this correctly.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — BRIEFING.md confirms "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" drives #7630.
- **Human preferences**: "Preference for direct/mechanical checks over indirect state files — 'just use PID, it's more direct.'" Aligns with ack-based health (PID check as secondary verification). "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose — 'any kind of cyclic work needs to be programmed deterministically.'" This is the foundational preference driving the entire EPIC.
- **Related learnings**: None directly constraining this audit.

## Audit Results — Point by Point

### (1) 5 events all L1 ✅ CONSISTENT

All three documents agree on exactly 5 event types (`assigned-to`, `stop-requested`, `shipped`, `version-bump`, `ack`), all at L1 (universal).

| Document | Location | Confirms |
|----------|----------|----------|
| PRD | §3.2, lines 297-303 | Event Types Table with all 5. "All events are L1 (universal)." |
| CONTEXT.md | Locked Decision #5, lines 40-53 | Explicit table of 5 types. "No L2/L3 event-reaction sub-skills needed." |
| TEST-PLAN.md | TC-1–TC-6 (lines 13-73), TC-40 (lines 454-461) | Category 1 is "5 Event Types." TC-40 validates all 5 in RECOGNIZED. |

### (2) No config gate 🚨 INCONSISTENT

**PRD says YES config gate.** CONTEXT.md says NO config gate. TEST-PLAN.md sides with CONTEXT.md.

| Document | Position | Evidence |
|----------|----------|----------|
| PRD | **Has config gate** | Line 83: `event-driven` (Event Driven → Enabled): "yes" \| "no" — default "no". Line 112: "graceful degradation... falls back to current behavior." Lines 724-727: "All behind event-driven config gate." Lines 733-736: full rollback procedure using `event-driven: no`. Line 849: vaults config gating as a reusable pattern. |
| CONTEXT.md | **No config gate** | Line 31: "No `event-driven: yes/no` config gate — event-driven is the only mode." Line 33: "Maintaining a config gate means maintaining two code paths indefinitely." Line 140: "No config gate: Event-driven is the only mode. No `event-driven: yes/no` flag." |
| TEST-PLAN.md | **No config gate** (implicit) | Line 642 (CQ-10): "There is no `event-driven` toggle." TC-37 expects event-driven templates unconditionally. TC-39 only tests graceful defaults for missing Event Driven section, not dual-mode behavior. No rollback test exists. |

**Severity: CRITICAL** — This is the foundational architectural decision and the docs directly contradict each other.

**Fix**: Update PRD to remove `event-driven` config field from §Upgrade & Migration (line 83), §Graceful degradation (line 112), §Config Gating (lines 740-745), §Migration steps (lines 724-727), §Rollback (lines 733-736), thin_launcher.py conditional prompt (lines 539-540), Vault Candidates (line 849), and all "event-driven: no" backward-compat references throughout §5.2. The config template (§5.4, lines 676-684) and FIELD_MAP (lines 688-693) are already correct (no `event-driven` field) — the inconsistency is internal to the PRD itself.

**PRD internal contradiction**: The PRD's config template (§5.4, line 676) lists exactly 5 fields without `event-driven`. The FIELD_MAP (line 688) also has only 5 entries. But the §Upgrade section (line 83) lists `event-driven` as the first config value. The PRD contradicts itself — fix by removing `event-driven` entirely.

### (3) No event-sensitivity ✅ CONSISTENT

None of the three documents include `event-sensitivity` as a config field or event type.

| Document | Position |
|----------|----------|
| PRD | No mention of `event-sensitivity` anywhere |
| CONTEXT.md | No mention of `event-sensitivity` anywhere |
| TEST-PLAN.md | CQ-10 (line 642): explicit negative — "There is no `event-driven` toggle and no `event-sensitivity` field." |

Note: The L1L4-REACTIONS.md document (a separate planning artifact) does mention `event-sensitivity` as a proposed soul_adaptation category, but that document is not part of the three-document audit set and was superseded by the 5-event L1-only model.

### (4) event-reactions.md deleted 🚨 INCONSISTENT

**PRD says DELETED.** TEST-PLAN.md references it as an active file for comprehension tests.

| Document | Position |
|----------|----------|
| PRD | Line 99: "Deleted sub-skills: `common/event-reactions` — deleted entirely, replaced by `common/event-driven-workflow`." Line 637: "Deleted sub-skill: `common/event-reactions.md`". Line 787: Phase 3 deliverable: "Deleted sub-skill: event-reactions.md." |
| CONTEXT.md | Line 51: "No L2/L3 event-reaction sub-skills needed." (implies but doesn't explicitly state deletion) |
| TEST-PLAN.md | **References event-reactions.md as live file**: CQ-3 (line 613), CQ-4 (line 617), CQ-5 (line 621), CQ-6 (line 625), CQ-8 (line 633), CQ-11 (line 645) — all list `references/sub-skills/common/event-reactions.md` as one of the "Files" a fresh QA agent should read to answer comprehension questions. |

**Severity: HIGH** — If QA spawns a fresh subagent and provides `event-reactions.md` (which still exists at `references/sub-skills/common/event-reactions.md` — verified), the agent will read the OLD event model (30+ event types, status-transition, pr-merged, etc.) and derive wrong answers that contradict the 5-event model. This renders CQ-3 through CQ-6, CQ-8, and CQ-11 invalid.

**Fix**: Remove all `references/sub-skills/common/event-reactions.md` references from CQ-3 (line 613), CQ-4 (line 617), CQ-5 (line 621), CQ-6 (line 625), CQ-8 (line 633), and CQ-11 (line 645). Replace with `references/sub-skills/common/event-driven-workflow.md` (the new file) and/or the relevant role instructions.

### (5) No Stop Grace Period ✅ CONSISTENT

None of the three documents include a "Stop Grace Period" as a design feature.

| Document | Position |
|----------|----------|
| PRD | No mention of "stop grace period" |
| CONTEXT.md | No mention. Locked Decision #2 (lines 27-28): stop-requested → agent finishes current event atomically → acks → process exits. No grace period between stop-requested and forced kill. |
| TEST-PLAN.md | No mention. TC-2, TC-3, TC-22 cover stop behavior without any grace period concept. |

Note: The GAP-REVIEW.md mentions a "shutdown grace period" as a race-condition concern (event loss between shutdown intent and kill), but this is a bug analysis, not a design feature. The L1L4-REACTIONS.md mentions a "grace period before forced kill" but that document is superseded.

### (6) No backward compat 🚨 INCONSISTENT

**PRD has extensive backward compat.** CONTEXT.md says NO backward compat. TEST-PLAN.md sides with CONTEXT.md.

| Document | Position |
|----------|----------|
| PRD | Lines 112: "Full backward compatibility for one version." Lines 513, 525: cycle_pre/post.py "retained for event-driven: no backward compat." Lines 724-727: phased migration with config gate. Lines 733-736: rollback procedure. Lines 795-796: dual-mode compose. Phase 4 cleanup (line 802-810): archive to legacy/. |
| CONTEXT.md | Line 31: "The old cycle code is removed, not retained for backward compat." Line 33: "If something breaks during development, fix it on the branch — that's what feature branches and QA are for." |
| TEST-PLAN.md | No backward-compat tests. No dual-mode tests. No rollback tests. TC-37 expects event-driven templates unconditionally. TC-38 upgrade sequence is one-directional (no rollback step). |

**Severity: CRITICAL** — This is a direct corollary of the config gate inconsistency. CONTEXT.md explicitly rejects backward compat; the PRD's extensive backward-compat machinery is dead weight per the Locked Decisions.

**Fix**: Same as issue (2) — remove all backward-compat references from PRD. Specifically: §Graceful degradation (line 112), cycle_pre/post.py retention notes (lines 513, 525), Migration steps 4-7 (lines 724-730), Rollback (lines 733-736), Phase 4 cleanup (lines 802-810), and Phasing Plan success criteria about dual-mode (lines 795-796). Phase 4 cleanup should become "remove" rather than "archive to legacy/."

### (7) ack replaces closure API and stopped event ✅ CONSISTENT

All three documents agree: ack is the universal closure mechanism, no dedicated `POST /events/{id}/complete` endpoint, no separate `stopped` event.

| Document | Location | Confirms |
|----------|----------|----------|
| PRD | §4.2 (line 399): "POST /events/{id}/complete endpoint from earlier PRD drafts is removed." §3.2 (line 308): "An ack of stop-requested = agent stopped. No separate stopped event needed." |
| CONTEXT.md | Locked Decision #4 (lines 35-38): "No dedicated closure endpoint (POST /events/{id}/complete is eliminated)." Locked Decision #2 (lines 27-28): "Harness recognizes an ack of a stop-requested event as shutdown confirmation." |
| TEST-PLAN.md | TC-6 (line 72): "POST /events/{id}/complete endpoint does not exist (endpoint was removed)." CQ-11 (line 646): "No separate stopped event is needed — ack is the universal closure mechanism that also serves as stop confirmation." |

### (8) Ack-based health ✅ CONSISTENT

All three documents agree: health monitoring is built into the ack protocol, no separate PID polling health watcher.

| Document | Location | Confirms |
|----------|----------|----------|
| PRD | §2.3 (line 254): "Ack-based: no ack within timeout → retry → after N retries → declare dead, kill PID, reboot." §3.2 (line 310): "Ack-based health monitoring. No separate health watcher polling PIDs." |
| CONTEXT.md | Locked Decision #8 (lines 61-68): "Ack-based health monitoring — replaces PID polling." Steps 1-4 match PRD exactly. Line 68: "PID check remains as a secondary verification before killing (OS-level truth)." |
| TEST-PLAN.md | Category 2 (lines 76-121), TC-7, TC-8, TC-9, TC-10: all validate ack timeout → retry → kill → reboot flow. TC-9 specifically validates PID-alive check before killing. |

### (9) External activity detector filters own changes ✅ CONSISTENT

All three documents agree: detector must filter SquidSquad's own GitHub activity.

| Document | Location | Confirms |
|----------|----------|----------|
| PRD | Risk 5 (lines 62-63): "Filter by squidsquad label and agent commit prefix. Must NOT react to SquidSquad's own changes." |
| CONTEXT.md | Locked Decision #9 (lines 73-74): "Filters by squidsquad label and agent commit prefix — must NOT react to SquidSquad's own changes." |
| TEST-PLAN.md | TC-12 (lines 138-145): filters agent commit prefix. TC-13 (lines 148-155): filters squidsquad-labeled issues/PRs. CQ-9 (lines 636-638): "Filters by squidsquad label (issues/PRs) and agent commit prefix pattern." |

### (10) Phased implementation ✅ CONSISTENT (with caveat)

All three documents agree on phased implementation. However, there's a tension between CONTEXT.md's "no config gate + keep loop alive until final phase" — these are hard to reconcile without SOME mechanism to switch between modes during development.

| Document | Location | Confirms |
|----------|----------|----------|
| PRD | §Phasing Plan (lines 748-817): Phase 1.5 → Phase 2 → Phase 3 → Phase 4. Uses config gate for coexistence. |
| CONTEXT.md | Locked Decision #15 (lines 99-100): "Phased implementation — keep the loop alive until the last phase. Each phase keeps the existing /loop cycle model alive alongside new event infrastructure." |
| TEST-PLAN.md | TC-36 (Phase 1.5 prereqs), TC-37 (compose output), TC-38 (upgrade sequence). No phase-gating tests. |

**Caveat**: CONTEXT.md Locked Decision #3 says "no config gate" and Locked Decision #15 says "keep the loop alive until the last phase." Without a config gate, how does the loop coexist with event-driven during phases 1.5-3? The PRD resolves this with the config gate (`event-driven: no` keeps loop, `event-driven: yes` uses events), but CONTEXT.md explicitly rejects that mechanism. This is a **latent design tension** the dev agent must resolve in the implementation plan. Possible resolution: during phases 1.5-2, the event infrastructure is built but the loop is still the only mode (no coexistence needed — just additive code). Phase 3 is where the switch happens atomically. The CONTEXT.md's "keep the loop alive" could mean "don't delete cycle code in phases 1-2, only in Phase 4."

**Severity: LOW** — Resolvable by the dev agent during implementation planning. The documents agree on the phased approach; only the coexistence mechanism is undefined.

## Additional Inconsistencies Discovered

### (A) 🚨 Who owns git push? — PRD vs CONTEXT.md vs TEST-PLAN.md

| Document | Position |
|----------|----------|
| PRD §2.3 (line 256) | "Agent commits after creative work; **harness pushes** after processing ack." |
| PRD §5.2 (line 519) | "Git commit/push → harness executes after processing ack" |
| CONTEXT.md Locked Decision #4 (lines 35-38) | "Agents do their own work and just signal completion. Rationale: agents already have full access to tracker.py, git_ops.py, and all mechanical scripts. Having the harness re-execute side effects from a payload is redundant complexity." — **implies agents push too.** |
| TEST-PLAN.md TC-34 (lines 387-394) | "Harness replays side effects (**git commit/push**) from persisted state." — **assumes harness does git operations.** |

**Severity: MEDIUM** — Affects implementation of ack processing and crash recovery. If agents push themselves, harness doesn't need git push logic. If harness pushes, it needs git authority and crash-recovery replay logic.

**Fix**: Decide one way and align all three. Recommendation in line with CONTEXT.md Locked Decision #4: agents handle all side effects (commit + push + tracker transitions + comments) during creative work, then just ack. Harness only tracks ack state. This eliminates the need for harness git push logic, simplifies crash recovery (no harness-side git replay), and aligns with the rationale that "agents already have full access." Update PRD §2.3 table and TEST-PLAN.md TC-34 accordingly.

### (B) 🚨 `events-atomic` mentioned as config field but not in FIELD_MAP or config template

| Document | Position |
|----------|----------|
| PRD §3.2 (line 325) | Lists `events-atomic: true` as a "Behavioral tuning default (L1, overridable at L4 via config.md)" |
| CONTEXT.md Locked Decision #10 (line 81) | Lists `events-atomic: true` alongside `scan-cooldown: 15` as config.md overrides |
| PRD §5.4 (lines 676-684) | Config template shows exactly 5 fields. `events-atomic` is **absent**. |
| PRD FIELD_MAP (lines 688-693) | 5 entries. `events-atomic` is **absent**. |
| TEST-PLAN.md CQ-10 (line 642) | "These are the **only 5 valid fields** in the ## Event Driven section." No `events-atomic`. |
| TEST-PLAN.md (entire doc) | Zero occurrences of `events-atomic`. No test case for it. |

**Severity: MEDIUM** — Two docs say `events-atomic` is a config field; the config template and FIELD_MAP and TEST-PLAN all say it isn't. If it's a behavioral default but NOT a config.md override (i.e., it's always `true` and not configurable), then PRD §3.2 and CONTEXT.md Locked Decision #10 should clarify this.

**Fix**: Either (a) add `events-atomic` to config template, FIELD_MAP, and TEST-PLAN CQ-10, or (b) remove the "overridable at L4 via config.md" language from PRD §3.2 (line 325-327) and CONTEXT.md Locked Decision #10. Given that event atomicity is a fundamental architectural invariant (Locked Decision #7), option (b) is recommended — `events-atomic` is not negotiable and should not be a config override. Document it as a hard constraint, not a tunable.

## Side Effects

- **Risk 1**: PRD's backward-compat references might confuse the dev agent into building a config gate that CONTEXT.md explicitly forbids — Severity: H — Mitigation: Fix PRD before implementation starts. Make CONTEXT.md the authoritative source (it captures Locked Decisions from human).
- **Risk 2**: QA runs comprehension tests using old `event-reactions.md` and validates against wrong event model — Severity: H — Mitigation: Fix CQ file references before QA phase.

## Edge Cases

- **CQ validation with deleted file**: If CQ-3 through CQ-6, CQ-8, and CQ-11 are executed as written, QA's fresh subagent reads `event-reactions.md` (old 30+ event model) and derives answers incompatible with the 5-event model. This will produce false-negative comprehension failures or false-positive passes depending on whether QA compares against the new or old expected answers.
- **Config template missing `event-driven` field during phased dev**: If the PRD's config template is followed (no `event-driven` field), and the CONTEXT.md says no config gate, then Phase 1.5-3 dev agents must develop event infrastructure alongside live loop without a toggle. This is feasible if phases are additive — new code doesn't activate until Phase 3 template switch. The dev agent must clarify this in the implementation plan.

## Integration Risks

- **Compose.py dual-mode removal**: If the config gate is removed per CONTEXT.md, compose.py no longer needs dual-mode output. This simplifies Phase 3 but removes the safety net PRD designed. CONTEXT.md decision #3 rationale ("fix it on the branch — that's what feature branches and QA are for") must be accepted.
- **Vault candidate #3 becomes invalid**: PRD line 849 vaults "Config gating for phased architectural migration" as a reusable pattern. If config gating is removed per CONTEXT.md, this vault candidate must be removed or rewritten.

## Upgrade & Migration

- **New config values**: PRD lists 6 (including `event-driven`), CONTEXT.md and TEST-PLAN.md list 5 (excluding `event-driven`). Per CONTEXT.md authority: 5 fields only.
- **New files**: Consistent across all three — `.squidsquad/.event-state.json`, `event-driven-workflow.md`, `event_poll.py`.
- **Template changes**: Consistent — cycle-runner removed, event-driven-workflow added, event-reactions deleted, instructions.md rewritten, includes.yml updated.
- **Upgrade steps**: PRD has rollback steps (lines 733-736). CONTEXT.md says no rollback (fix forward). TEST-PLAN.md TC-38 is one-directional. Per CONTEXT.md authority: remove PRD rollback steps.
- **Graceful degradation**: PRD line 112 describes backward compat. CONTEXT.md line 140 says no config gate. Per CONTEXT.md: remove graceful degradation section.

## Open Questions

- **Q1**: How does "keep the loop alive until the last phase" (CONTEXT.md LD#15) coexist with "no config gate" (CONTEXT.md LD#3)? — **Why**: If there's no toggle, and the loop is alive during Phases 1.5-2, what prevents agents from using event-driven mode prematurely? Does "alive" mean the code exists but isn't composed into templates? The dev agent needs explicit guidance on the coexistence mechanism during development phases.

## Recommendation

**Needs rethinking** — specifically, the PRD must be updated to align with CONTEXT.md as authoritative. The PRD was written before the CONTEXT.md Locked Decisions were finalized, and it retains design elements (config gate, backward compat, harness-owned git push) that were explicitly overridden. Five concrete fixes required:

1. **PRD**: Remove `event-driven` config field, all backward-compat references, config gating, rollback procedure, and graceful degradation. Align with CONTEXT.md Locked Decision #3.
2. **PRD**: Resolve git push ownership — recommend agents push per CONTEXT.md LD#4. Update §2.3 table and §5.2 cycle_post.py absorption.
3. **PRD**: Remove or clarify `events-atomic` as a config.md override (make it a hard invariant, not a tunable).
4. **TEST-PLAN.md**: Fix CQ-3, CQ-4, CQ-5, CQ-6, CQ-8, CQ-11 to reference `event-driven-workflow.md` instead of `event-reactions.md`.
5. **TEST-PLAN.md**: TC-34 should be revised to reflect agent-owned git push (or removed if harness no longer does git operations).

## Vault Candidates

- **Type**: learning — **PRD/CONTEXT/TEST-PLAN cross-audit finds config gate disagreement as the dominant inconsistency source** — **Why**: The config gate (`event-driven: yes/no`) permeates ~15 PRD sections. When CONTEXT.md overrode it, the PRD was not updated, creating a cascade of secondary inconsistencies (backward compat, rollback, dual-mode compose, graceful degradation). This is a reusable lesson: when a Locked Decision overrides a mechanism that appears in many sections, do a grep-and-replace audit across all planning documents, not just the CONTEXT.md.
- **Type**: learning — **Comprehension tests must reference post-migration files, not pre-migration files** — **Why**: TEST-PLAN.md's CQ questions still reference `event-reactions.md` which the PRD declares deleted. When template migration is part of the feature, comprehension test file references are a canary for stale artifacts. A checklist item for future TEST-PLAN authors: "grep all CQ file references against the 'Deleted sub-skills' section of the PRD."
- **Type**: pattern — **CONTEXT.md as authoritative source for post-human-decision consistency** — **Why**: The CONTEXT.md captures Locked Decisions from the human. When PRD and CONTEXT.md disagree, CONTEXT.md wins. This should be stated explicitly in the PRD template or in a project convention. Currently the PRD still has a Vault Candidate (line 849) that praises config gating — a pattern the human explicitly rejected.