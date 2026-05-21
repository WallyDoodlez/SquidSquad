# RESEARCH-9478 — Remove branch_workflow=off code paths

**Issue**: #9478
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-21 (cycle 1538)

---

## 1. Question

The `branch-workflow` config option toggles between "feature branch + PR per task" (yes) and "everything on main" (no). The "no" path is never used in practice and is a foot-gun (latent bug #8691 dropped skill code when `branch_workflow=False`). Remove the disabled-mode code paths entirely; make branch+PR the only mode.

Human direction (cycle 1515): "I really don't think we will want to ever work without our workflow. I plan to remove that option completely."

---

## 2. The Surface (Grounded)

### 2.1 Scripts referencing `branch-workflow` (7 files)

| File | Lines | What it does |
|------|-------|--------------|
| `references/scripts/config.py` | 68 | Field map entry mapping legacy key path |
| `references/scripts/cycle_pre.py` | 164-165 | Early-return guard for the branch-correction logic |
| `references/scripts/cycle_post.py` | 454-465 | Gate on the skill split-commit path |
| `references/scripts/git_ops.py` | 749-770 | `task_begin` no-op-when-disabled guard |
| `references/scripts/git_ops.py` | 829-880 | `task_end` no-op-when-disabled guard |
| `references/scripts/harness.py` | 1377 | Exposes the flag in `/status` JSON |
| `references/scripts/tracker.py` | 696 | `_is_branch_workflow_enabled()` helper, used to gate `_check_unmerged_branch` and similar |
| `references/scripts/wizard.py` | 1957, 2340-2342, 2430 | Setup-time prompt + JSON command emitter |

### 2.2 Sub-skill instruction fragments (9 files)

| File | Mentions |
|------|----------|
| `references/sub-skills/common/cycle-runner.md` | Conditional language about commit semantics |
| `references/sub-skills/common/git-commit.md` | Conditional language |
| `references/sub-skills/roles/dev/implement-tasks.md` | "If branch workflow enabled, …" instructions |
| `references/sub-skills/roles/dev/triage-issues.md` | Similar |
| `references/sub-skills/roles/dm/delivery-packaging.md` | Conditional language |
| `references/sub-skills/roles/dm/git-commit.md` | Similar |
| `references/sub-skills/roles/pm/pipeline-sentinel.md` | PR-conflict detection only runs when branch_workflow=yes (line ~459 in old PM CLAUDE.md) |
| `references/sub-skills/roles/qa/git-commit.md` | Conditional language |
| `references/sub-skills/roles/qa/verification.md` | Conditional language |

### 2.3 Documentation surface

- `SKILL.md` lines 282, 293 — describes Branch Workflow alongside Auto Merge in the operating modes
- `.squidsquad/config.md` lines 57-59 — `## Branch Workflow` section with `Enabled: yes`

### 2.4 Tests referencing `branch-workflow`

- `tests/test_config_functions.py` — real tests on the field
- `tests/test_comprehension_2195.py` — CQ test
- `tests/comprehension/8697_fixtures/*_CLAUDE.md` (8 files) — fixture CLAUDE.md content used by CQ tests; may have conditional `branch_workflow: yes` mentions in their composed content

### 2.5 Latent bug subsumed by removal

`#8691 ERROR fix` in PR #8812 (closed) addressed: skill code silently dropped when `branch_workflow=False` because skill is "intentionally absent" from `git_ops.py:_role_owned_patterns` (line 574). Removing the disabled-mode code path makes this bug unreachable by construction. PR #8812's other findings (#8653, #8664, #8689, #8699) were robustness warnings, mostly orthogonal — they should be re-audited against current main and re-filed individually if still applicable. None of them block #9478.

---

## 3. Dead Code Inventory (What Gets Removed)

For each branch-workflow gate, the "disabled" branch becomes dead code. Concretely:

### 3.1 Scripts

- **`config.py:68`** — remove the `branch-workflow` entry from the field map (or leave it and let it warn-and-ignore on read).
- **`cycle_pre.py:164-165`** — delete the `if not branch_workflow: return None` guard. The branch-correction code that follows runs unconditionally.
- **`cycle_post.py:454-465`** — delete the `branch_workflow = False; try: ...` block AND the `and branch_workflow` part of the `if role == "skill" and branch_workflow and code_commit:` check. Skill split-commit path becomes always-on.
- **`git_ops.py:749-770`** — `task_begin`: delete the early-return guard. Function body always runs.
- **`git_ops.py:829-880`** — `task_end`: same deletion.
- **`harness.py:1377`** — remove the `branch_workflow` key from `/status` response. (Or keep for backward-compat with old clients, hardcoded `True`.)
- **`tracker.py:696`** — delete `_is_branch_workflow_enabled()`. Callers (`_check_unmerged_branch` etc.) drop the guard call.
- **`wizard.py:1957, 2340-2342, 2430`** — delete `branch_workflow_prompt`, `cmd_branch_workflow_prompt`, and the dispatcher entry. Setup wizard no longer asks the question.

### 3.2 Sub-skill fragments

Each of the 9 fragments has conditional language like "If Branch Workflow is enabled, then…". Each such conditional needs to be rewritten to unconditional language (drop the "if" prefix, keep the enabled branch as the only content).

### 3.3 Documentation

- `SKILL.md` — language rewritten to describe branch+PR as the only mode, no longer paired with Auto Merge as a configurable toggle.
- `.squidsquad/config.md` lines 57-59 — delete the `## Branch Workflow` section entirely. Old config files with the field stay valid (config.py warn-and-ignores unknown keys).

### 3.4 Tests

- `tests/test_config_functions.py` — drop tests asserting branch-workflow field behavior.
- `tests/test_comprehension_2195.py` — audit; rewrite if it depends on the toggle.
- `tests/comprehension/8697_fixtures/*_CLAUDE.md` — these are composed CLAUDE.md snapshots; regenerate from compose.py after the sub-skill changes land.

---

## 4. Migration Considerations

### 4.1 Existing user `config.md` files

Operators who installed earlier have `## Branch Workflow\n- **Enabled**: yes` in their `config.md`. After removal:
- The field is no longer read. Nothing breaks.
- The wizard no longer adds it to new configs.
- Stale configs are silently accepted; the field is just unused.

If we wanted to be strict, the wizard could detect the stale field and offer to remove it on upgrade. But that's polish, not blocker.

### 4.2 Live agents at upgrade boundary

Agents currently running have the OLD CLAUDE.md in their session context (loaded at boot). After upgrade:
- Operator reboots all 4 agents (standard ship procedure).
- Fresh sessions load the new CLAUDE.md with the always-on branch language.
- No mid-session reload mechanism needed (we accepted this restart-as-reload semantics in #9588 D2).

### 4.3 PR #8812 (the stale orphan)

Filed 2026-05-18 to fix #8691 ERROR (skill code dropped on branch_workflow=False). After #9478 ships, that bug is unreachable, so #8812 becomes superseded.

PR #8812 should be closed without merge (already commented on it 2026-05-20 marking as superseded by #9478 / #9580; close action remained pending). #9478's ship can include the close action.

The other #8812 findings (#8653, #8664, #8689, #8699) — robustness warnings against code that's evolved substantially since #8812 was cut. **Not in scope of #9478.** Re-audit and re-file separately if still applicable.

### 4.4 Tests fixture regeneration

`tests/comprehension/8697_fixtures/*_CLAUDE.md` are snapshots of composed CLAUDE.md. They will diverge from current compose output once sub-skill fragments are rewritten. Regenerate via `python references/scripts/compose.py deploy <role>` for each role and update fixtures. Add this to skill's PR.

---

## 5. Options Surveyed

### Option A — Mechanical removal in one PR

Single PR removes everything: scripts, sub-skills, docs, tests, fixtures. ~20 files changed. Comprehensive, single review.

**Pros**: clean cutover; no partial-state surface.
**Cons**: large PR; harder to review; if any single file has subtle interaction we missed, harder to bisect.

### Option B — Layered ship (scripts first, then sub-skills, then docs)

PR 1: scripts only (the dead-code removal). PR 2: sub-skill rewrites. PR 3: doc cleanup + fixture regen.

**Pros**: easier review per PR; faster initial ship.
**Cons**: between PR 1 and PR 2, sub-skill instructions reference behavior that no longer exists in code — agents may be confused. Risky window.

### Option C — Same as A, but split skill from sub-skills

PR 1: scripts + tests + fixtures (the code surface). PR 2: sub-skills + docs (the instruction surface).

**Pros**: smaller PRs than A; no behavior gap (sub-skill conditionals still work, just always select the "enabled" branch since the field is gone but the conditional reading of `Branch Workflow: yes` defaults to true).
**Cons**: still two PRs; relies on the sub-skill conditionals being robust during the gap.

### Option D — Behind a feature flag for one release, then remove

Land "always-on" behavior gated by a new flag default `True`. After a release cycle, remove the gate.

**Pros**: rollback safety.
**Cons**: doubles the surface (adds a flag, then removes it); we have zero need for rollback safety given live operators are all on `branch-workflow: yes` already.

### Recommendation

**Option A (mechanical removal in one PR)**. Reasons:
- The change is mechanical — deletions, not new code paths.
- No live operator is on the `off` path, so no behavior regression risk for existing users.
- The PR's deletion footprint is large (~20 files) but each individual deletion is small and obvious. Review effort scales with code size, not file count.
- Single PR keeps related changes atomic.

---

## 6. Open Questions for CONTEXT (Phase 2)

1. **Config-field cleanup vs warn-and-ignore for existing `config.md` files?**
   - PM rec: **silently ignore** the stale field. No active cleanup needed; the field just won't be read. Wizard no longer adds it to new installs.

2. **Keep `branch_workflow` key in `/status` JSON for backward-compat (hardcoded `True`)?**
   - PM rec: **remove entirely.** No external consumers identified. If anyone needs it, can re-add later.

3. **Should the wizard prompt user during upgrade to remove the stale field?**
   - PM rec: **no** — adds friction, no real benefit, the field is silently ignored anyway.

4. **Test fixture regeneration approach?**
   - PM rec: regenerate `tests/comprehension/8697_fixtures/*_CLAUDE.md` via `python references/scripts/compose.py deploy <role>` after sub-skill rewrites land. Include the regenerated fixtures in the PR.

5. **PR #8812 closure timing — close during this PR or separately?**
   - PM rec: **close during this PR.** The original task is superseded by #9478; clean up the loose end together. Reference #9478 in the close comment.

6. **Other #8812 findings (#8653, #8664, #8689, #8699) — re-audit in scope of #9478 or separately?**
   - PM rec: **separately.** #9478 is scoped to the dead-code removal. The other findings need fresh audit against current main and individual triage; bundling them here adds scope.

7. **Hard cutover vs deprecation marker?**
   - PM rec: **hard cutover.** Per D5 from #9588 (same pattern).

8. **Live-agent migration: reboot needed?**
   - PM rec: **yes, reboot all 4 agents** as part of the ship. Standard ship-procedure already.

---

## 7. Dependencies

- All 7 scripts listed in §2.1.
- All 9 sub-skill fragments in §2.2.
- `SKILL.md`, `.squidsquad/config.md`.
- Tests + 8 fixture CLAUDE.md files in `tests/comprehension/8697_fixtures/`.
- Stale PR #8812 — close as superseded.

---

## 8. Non-Goals

- Re-auditing #8812's other findings (#8653 / #8664 / #8689 / #8699). Separate.
- Adding new config fields or new modes. Pure removal.
- Refactoring the skill split-commit logic itself (it just becomes always-on; no internal changes).
- Adding new tests beyond updating existing ones + regenerating fixtures.
- Changing `auto-merge` or `pr-flow` config (those describe PR semantics, not branch usage; out of scope).

---

## 9. Risks

1. **Sub-skill rewrites introduce LLM-prompt-following bugs.** Removing conditional language ("if branch_workflow then X else Y") may inadvertently change the imperative weight. Mitigation: rewrite to be MORE imperative ("Always do X"), not less.
2. **Test fixture regeneration may drift from CLAUDE.md if not committed atomically.** Mitigation: regenerate in the same PR; CI catches mismatches.
3. **PR #8812's open state is a distraction for any agent scanning the queue.** Mitigation: close in #9478's commit.
4. **Existing test that asserts `branch_workflow=False` behavior** — must update or delete. Mitigation: audit `tests/test_config_functions.py` etc., remove dead assertions.
5. **`compose.py` event-contract validation may rely on branch-workflow field** indirectly. Mitigation: search for downstream dependencies before removal; if found, surface separately.

---

## 10. Next Step

Write CONTEXT-9478.md locking the chosen approach + answers to the 8 questions. Then transition pending → planning → planned and present to human for approval.
