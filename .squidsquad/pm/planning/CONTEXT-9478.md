# CONTEXT-9478 — Remove branch_workflow=off code paths

**Issue**: #9478
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21 (cycle 1538)
**Status**: pending → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9478 + this CONTEXT-9478.md combined are the contract for skill at pickup.

---

## 1. Locked Decisions

### D1. Stale `Branch Workflow` field in existing `config.md` — ACTIVE CLEANUP

**Locked: skill's PR removes the `## Branch Workflow` section from `.squidsquad/config.md` directly** as part of the same commit. Not silent ignore — active cleanup to avoid context pollution.

Reasoning: agents read `config.md` as context. Leaving a dead `Branch Workflow: Enabled: yes` line creates lingering instruction-context for the model. Cleaner to delete now.

Concrete edit: delete lines 57-60 of `.squidsquad/config.md`:
```
## Branch Workflow

- **Enabled**: yes

```

### D2. `/status` JSON `branch_workflow` key — REMOVED

**Locked: remove the `branch_workflow` field from harness `/status` response.** No external consumers identified. Deletion is at `references/scripts/harness.py:1377` (`result["branch_workflow"] = ...`).

### D3. Upgrade wizard cleanup logic — NOT NEEDED

**Locked: no upgrade-wizard logic to detect stale fields.** Per human direction: no install base yet, no upgrade migration story required.

### D4. Test fixture regeneration — IN PR

**Locked: skill regenerates `tests/comprehension/8697_fixtures/*_CLAUDE.md` via `python references/scripts/compose.py deploy <role>` after sub-skill rewrites land.** Includes regenerated fixtures in the same PR. CI catches any drift.

Commands skill will run:
```bash
python references/scripts/compose.py deploy pm
python references/scripts/compose.py deploy skill
python references/scripts/compose.py deploy qa
python references/scripts/compose.py deploy dm
# Then copy/diff the composed output into tests/comprehension/8697_fixtures/<role>_polling_CLAUDE.md
# (and ..._events_CLAUDE.md if any event-mode fixtures touched the surface)
```

### D5. PR #8812 closure timing — DURING THIS PR

**Locked: close PR #8812 as part of #9478's ship.** The original #8691 ERROR (skill code dropped on `branch_workflow=False`) becomes unreachable by construction. Closure comment references #9478 as the superseding work.

### D6. Other #8812 findings — SEPARATE FROM #9478

**Locked: out of scope.** Findings #8653 (state-conflict resolution), #8664 (test_volatile assert), #8689 (restart endpoint), #8699 (manifest dedup) were DeepSeek-verified real but are robustness warnings against code that has evolved substantially since #8812 was cut. Re-audit against current main and re-file individually if still applicable. None block #9478.

### D7. Cutover style — HARD CUTOVER

**Locked: hard cutover.** Single PR ships everything. No feature flag, no deprecation marker. Same pattern as #9588 D5.

### D8. Live-agent reboot — YES, AS PART OF FLEET RESET

**Locked: reboot all 4 agents after #9478 merges.** Standard ship procedure. Per Q9 below (NEW), this reboot is coordinated with the broader fleet-reset prep for the event-driven flip.

### D9. (NEW) Fleet-reset coordination for event-driven flip

**Locked: #9478's required agent reboots are deferred and coordinated with the fleet-wide reset for the event-driven flip.**

Sequence (deferred until all blockers ship):
1. **#9725** ships — agents actually invoke `/loop` on boot.
2. **#9478** ships — clean ship (this issue).
3. **#9415** ships — collision-resistant ids.
4. **#9588** + **#9688** already shipped.
5. **Coordinated fleet reset**:
   - Stop all 4 agents (kill claude.exe trees via `boot_remote` stop or manual taskkill).
   - Stop harness (`squidsquad shutdown` or kill `harness.py`).
   - Flip `event-driven: yes` in `.squidsquad/config.md`.
   - Restart harness fresh.
   - Spawn all 4 agents via `boot_remote.py --all`. They boot into event-driven mode via the #9588 bootstrap; harness wakes them via Monitor.
6. **Watch for ~2 hours** to confirm event-driven mode is stable + agents are cycling correctly.

This converges all five shipped+approved items into a single deployment moment. Reduces churn vs sequential reboots after each individual ship.

**Implication for #9478 implementation**: skill ships the code/sub-skill/doc changes + closes PR #8812, but does NOT itself reboot agents. Reboots happen later as part of the fleet reset. Skill's #9478 PR comment notes "agent reboot deferred to fleet reset" so QA + DM know not to drive an immediate reboot.

---

## 2. Grounded File References

### 2.1 Scripts to modify

- `references/scripts/config.py:68` — remove `branch-workflow` field map entry
- `references/scripts/cycle_pre.py:164-165` — remove `if not branch_workflow: return None` guard
- `references/scripts/cycle_post.py:454-465` — remove the `branch_workflow = False; try: ...` block; simplify the `if role == "skill" and branch_workflow and code_commit:` to drop `and branch_workflow`
- `references/scripts/git_ops.py:749-770` (`task_begin`) — remove no-op-when-disabled guard
- `references/scripts/git_ops.py:829-880` (`task_end`) — same
- `references/scripts/harness.py:1377` — remove `branch_workflow` from `/status` response
- `references/scripts/tracker.py:696` — delete `_is_branch_workflow_enabled()` helper; callers drop the guard call
- `references/scripts/wizard.py:1957, 2340-2342, 2430` — delete `branch_workflow_prompt()`, `cmd_branch_workflow_prompt()`, and the dispatcher entry

### 2.2 Sub-skill fragments to rewrite

Each rewrite changes conditional language to unconditional imperative:

- `references/sub-skills/common/cycle-runner.md`
- `references/sub-skills/common/git-commit.md`
- `references/sub-skills/roles/dev/implement-tasks.md`
- `references/sub-skills/roles/dev/triage-issues.md`
- `references/sub-skills/roles/dm/delivery-packaging.md`
- `references/sub-skills/roles/dm/git-commit.md`
- `references/sub-skills/roles/pm/pipeline-sentinel.md` — drop the "if branch_workflow" guard around PR-conflict detection (PR conflict detection always runs)
- `references/sub-skills/roles/qa/git-commit.md`
- `references/sub-skills/roles/qa/verification.md`

Pattern for each: locate "If Branch Workflow is enabled, …" or "When `branch-workflow: yes`, …" phrases. Remove the conditional clause; keep the body content as the only directive.

### 2.3 Documentation

- `SKILL.md` lines 282, 293 — rewrite to describe branch+PR as the only mode, no longer paired with Auto Merge as a configurable toggle
- `.squidsquad/config.md` lines 57-60 — delete the `## Branch Workflow` section entirely (per D1)

### 2.4 Tests

- `tests/test_config_functions.py` — audit for `branch-workflow` assertions; drop dead tests
- `tests/test_comprehension_2195.py` — audit; rewrite if it depends on the toggle
- `tests/comprehension/8697_fixtures/{pm,skill,qa,dm}_polling_CLAUDE.md` — regenerate per D4
- `tests/comprehension/8697_fixtures/{pm,skill,qa,dm}_events_CLAUDE.md` — regenerate if event-mode fixtures touched

### 2.5 PR #8812

Close as superseded by #9478 (D5). Closure comment template:
> Closing as superseded by #9478. The #8691 ERROR fix (skill code dropped when branch_workflow=False) becomes unreachable by construction once the disabled-mode code paths are removed. Other findings (#8653/#8664/#8689/#8699) re-audit separately against current main.

---

## 3. Acceptance

- All 7 scripts edited per §2.1; no `branch-workflow` references remain.
- All 9 sub-skill fragments rewritten per §2.2; no conditional language about branch workflow.
- `SKILL.md` updated; `.squidsquad/config.md` has the `## Branch Workflow` section removed.
- `tests/comprehension/8697_fixtures/*_CLAUDE.md` regenerated to match new compose output.
- Test suite passes; dead branch-workflow tests removed.
- `grep -rn "branch.workflow\|branch_workflow" references/ tests/` returns only comments or none.
- PR #8812 closed with supersede comment.
- Skill comments on #9478: "Agent reboot deferred to fleet reset per CONTEXT D9."

---

## 4. Out of Scope

- Re-auditing #8812's other findings (separate disposition).
- Adding/changing other config fields.
- Refactoring the skill split-commit logic itself (becomes always-on; no internal change).
- Implementing the fleet reset (separate operational task once all blockers ship).
- Touching `auto-merge` or `pr-flow` config (separate concerns).

---

## 5. Sequencing

1. **Ship #9478** independently. Implementation is mechanical.
2. After ship, **do NOT reboot agents** immediately. Coordinated reboot is part of fleet reset (D9).
3. **Wait for #9725** (spawn-prompt fix) + **#9415** (event id widening) to also ship.
4. **Fleet reset** (D9 step 5) coordinates the event-driven flip + reboots all 4 agents fresh.

---

## 6. Risk Notes (for skill at pickup)

1. **Sub-skill rewrites must preserve imperative weight.** Removing "If X, then Y" → bare "Y" is fine if Y is already an imperative. If Y was buried in a conditional, hoist it.
2. **Test fixture regeneration drift**: regen MUST happen in the same PR. If sub-skill rewrites are committed but fixtures aren't regenerated, CI on comprehension tests will fail.
3. **`config.py` field-map cleanup**: removing the entry is the right cleanup but verify nothing reads it via a stringly-typed path that the type checker wouldn't catch.
4. **Wizard JSON commands**: `branch_workflow_prompt` is also wired to a CLI command (`cmd_branch_workflow_prompt`). Both delete together.
5. **Live operator running an old setup wizard** would still get the prompt; mitigation: also remove from wizard's dispatcher (`references/scripts/wizard.py:2430`).
6. **PR #8812 close**: do this LAST in the PR sequence so the closure references the merged #9478 commit.

---

## 7. Open Questions Resolved

| Q | Locked |
|---|--------|
| Q1 | **ACTIVE CLEANUP** — remove `## Branch Workflow` section from `.squidsquad/config.md` directly |
| Q2 | Remove `branch_workflow` from `/status` JSON entirely |
| Q3 | No upgrade-wizard logic (no install base yet) |
| Q4 | Regenerate fixtures via `compose.py deploy` in same PR |
| Q5 | Close PR #8812 during #9478's ship |
| Q6 | Other #8812 findings separate from #9478 |
| Q7 | Hard cutover |
| Q8 | Reboot agents deferred to fleet reset (D9) |
| Q9 | **NEW** Fleet reset coordinated after #9725 + #9478 + #9415 all ship |

---

## 8. Next Step

PM transitions #9478 status:pending → planning → planned. Human reviews CONTEXT-9478.md. On approval, transition planned → approved. Skill picks up.

After all five issues ship (#9588 + #9688 + #9725 + #9415 + #9478), PM coordinates the fleet reset per D9.
