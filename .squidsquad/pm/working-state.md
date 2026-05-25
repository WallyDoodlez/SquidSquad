# Working State

- **Task**: Doc-architecture cluster (#9968 / #9996 / #9998 / #9969 / #9970) under plan-first hold awaiting human decisions. #9965 awaiting human AC2.4-2.7 STOP-lift.
- **Status**: holding all structural moves; four human decisions pending (see queue below)
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-24 02:46, cycle 1629 end)

- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external untriaged
- 1 approved (long-running, DM lane): #3 (going-public)
- 2 in-progress:
  - **#9965** (skill, 6274.2 / AC2.8) — option-3 carve-out DONE. Suite at 5 reds, all in test_wizard.py coupled to wizard.py D4 (frozen by STOP). Skill cycle 1338 ack'd PM no-transition; quiet on improvement-scan cycles awaiting human STOP-lift.
  - **#9968** (PM, EPIC L1-L4 doc) — effectively superseded by #9996+#9998. NOT closed per plan-first hold.
- 2 pending tasks (PM, discussion-phase):
  - **#9996** — Preset catalog drift vs L3 + INSTALLER-ARCH
  - **#9998** — Multi-worker / multi-verifier doc gap + Q1-Q5 lock + 2 follow-up findings (§2 sub-skill/manifest drift, sub-skill-vs-L1-L4 separation reframe)
- 1 pending (gated): #9966 (6274.3) — gated on 6274.2 merge + cutover window
- 2 planning (skill, stale): #9874 (harness arch review), #9875 (L2 vault writeback)
- 1 planned (skill, stale): #9845 — withholding nudge until #9968/#9998 settles
- 2 issues at status:open: #9969 (manifest.md naming), #9970 (composed-md drift)
- **shipped_since_bump**: 8 of 10 (under threshold)
- Recently shipped this session: #9967 (cursor-evicted fix), #9999 (ship-gate squash-merge fix)

## Pending human decisions (in order)

1. **#9965 — AC2.4-2.7 STOP-lift?** Option-3 cleared 9 of 14 reds. Final 5 in `test_wizard.py` couple to wizard.py D4, frozen by 2026-05-23 15:43Z STOP directive. Lift → skill finishes → 0 fails → pending-test → ship.
2. **#9996 + #9998 — discussion-phase pickup?** HELD per plan-first; awaiting doc-coverage audit before transition.
3. **#9968 — close as superseded?** HELD per plan-first.
4. **Doc-coverage audit shape**: option (i) PM-alone over multiple cycles, or option (ii) PM scopes + spawns parallel subagents. Whether to draft audit scaffold first.

## Locked architectural decisions this session (#9998 contract)

These are locked in tracker comments on #9998 (cycles 1623-1627):

### Q1-Q5 answers

- **Q1 (routing target)**: route by class; instance picking is post-routing coordination.
- **Q2 (EAD)**: EAD always routes to class. **NEW rule**: human comment on issue → `target_class=pm`, `event_context="human-message"`; PM triages including patching missing `role:*` labels.
- **Q3 (care filter)**: class-level (`event.target_class == my_class`); each instance has unique name for ack/coordination.
- **Q4 (bus contract permission)**: keyed by class (follows from uniformity); team roster manifest must enforce unique instance names when class count > 1.
- **Q5 (subloop)**: exactly one designated `subloop_runner` per class declared in team roster.

### Architectural rules (new)

- **Same-class agents = SCALING, not SPECIALIZATION.** Multiple `dev` agents are identical replicas for throughput, NOT `fe-dev` + `be-dev`. Specialization lives at the class level (separate `fe` and `be` classes) or not at all.
- **Composed-output uniformity guarantee.** All instances of same class share byte-identical composed CLAUDE.md (except instance-name fields). compose.py needs `verify-class-uniformity` step.

### Doc-drift findings on #9998

- **§2 phrasing**: `references/sub-skills/common/` has no L1/L2 split on disk; `manifest.md` isn't really L1, it's compose plumbing; manifest.md is being superseded by per-role `includes.yml`. Three resolution options (A: physical split, B: clarify conceptual, C: drop L1/L2 distinction).
- **Sub-skill separation reframe**: COMPOSE-ARCHITECTURE.md conflates "instruction layering" (L1-L4) with "sub-skill catalog" (reusable how-tos). Rewrite §2 to be instruction-layering only; sub-skills move to their own section with current-state (inlined) vs target-state (real Claude skills via SKILL.md + .claude/skills/) called out.

### Scope adds surfaced

- Preset manifest schema needs `count`, optional `instance_names`, `subloop_runner` fields.
- PM L2 responsibility doc needs "human-message triage" section.
- compose.py needs `verify-class-uniformity` step.
- INSTALLER-ARCH.md §1.1 needs "scaling not specialization" clarification.

## Plan-first hold (feedback_plan_first, saved cycle 1627)

User explicit preference: no closing/merging/transitioning until docs demonstrably cover all functionality without gaps. Proposed two-pass functional-coverage audit:
- Pass 1: inventory every functional surface (from codebase + shipped behaviors + locked decisions). Output ~40-60 surfaces.
- Pass 2: map each surface → owning doc + verdict (COVERED / PARTIAL / MISSING / DRIFTED / WRONG-DOC / DUPLICATED).

User has not yet picked option (i) vs (ii) or confirmed audit scaffold. NO audit work has started.

## #9965 option-3 trace (for context)

- (3a) cycle 1332 commit 2afacb77: preset YAML `[dev]→[worker]` + 7-8 feat328 tests
- (3b) cycle 1333: two compose.py disk-check shims + 3 test_compose tests
- (3c) cycle 1335: WIZARD.md prose + lock test + 6th untracked fail caught
- (3c) DS fix-up commit 9aae44ba: verifier roster placement + forbidden-token coverage
- Remaining 5 reds: TestScaffoldInstallDevVariants x3 + TestScaffoldL4Files x2 (all wizard.py D4)

## Recently shipped this session (verified)

- **#9967** — harness `event_bus_reader.query()` honors eviction signal (cursor-stuck fix). Cursor in this session still shows df9f33751a6a because our session predates the deploy.
- **#9999** — ship-gate accepts squash-merged PRs (false-positive ancestry check). QA cycle 809 verified; DM PR #10000 squash-merged.

## Errors made this session (to avoid repeating)

- **Cycle 1628 false "no QA installed"**: grepped config.md for "Dev Agents" line only; missed "QA: always present" two rows up. Retracted in cycle 1629 working state. Lesson per `feedback_trust_script_output`: trust authoritative state (gh issue view, full file read), not partial grep.
- **Same cycle, "QA stalled" pivot**: read `bootup_complete: false` from harness-state and stale `.claude-pid` mtime; concluded wedge; user corrected — QA was alive and had already verified #9999 (cycle 809). Should have checked tracker state first.
- **4-cycle PM miss on #9965 cycle 1322 wizard-bundle question** (caught cycle 1623): PM was deep in #9968 doc work and skipping skill issue comments. Memory `feedback_read_issue_comments` already encodes the discipline; execution failed.

## #9968 / #9996 / #9998 convergence note

#9998's locked contract now substantively IS the #9968 doc-rewrite scope. When discussion-phase opens, recommend closing #9968 (umbrella) in favor of #9996 (preset catalog) + #9998 (doc rewrite contract). HELD per plan-first.

## Active session conversation thread

Compose-arch §2 questions answered + locked on tracker. Last open question to user: "Want me to draft the audit scaffold (inventory categories + matrix template) so we have a concrete artifact to fill in?" — not yet answered.
