# Working State

- **Task**: #9478 — Remove branch_workflow=off code paths (CONTEXT-9478 D1-D9)
- **Status**: in-progress (multi-cycle)
- **Branch**: squidsquad/task/9478
- **Started**: 2026-05-21 01:02
- **Last Processed Event ID**: 9d7c2489

## Slice plan (committable units)

1. **Slice A — scripts (this cycle)**: config.py, cycle_pre.py, cycle_post.py, git_ops.py, harness.py, tracker.py, wizard.py. All deletions / unconditional simplifications per CONTEXT §2.1. ~7 small edits.
2. **Slice B — sub-skills + recompose + fixtures (next cycle)**: 9 sub-skill fragments per CONTEXT §2.2. Remove conditional language. Recompose 4 roles. Regenerate 8 comprehension fixtures.
3. **Slice C — docs + tests audit + PR #8812 closure**: SKILL.md, .squidsquad/config.md, test audit (test_config_functions.py, test_comprehension_2195.py), close PR #8812 per D5.

## Slice A progress (cycle 1207) — COMPLETE

- [x] config.py:68 — removed `branch-workflow` field map entry
- [x] cycle_pre.py — removed L164-165 guard AND L497 `branch_workflow` flag in `_read_config_flags()`
- [x] cycle_post.py — removed L454-459 read+flag, simplified `if role == "skill" and branch_workflow ...` → `if role == "skill" and code_commit`; removed L202-204 toggle in `_verify_remote_branch`
- [x] git_ops.py — removed no-op-when-disabled guards in `task_begin` (L785-793) and `task_end` (L852-860); kept comment at L554 ("fatal for branch workflow") as descriptive prose
- [x] harness.py:1377 — removed `branch_workflow` from /status JSON response
- [x] tracker.py — deleted `_is_branch_workflow_enabled()` helper + the L722 guard in `_check_unmerged_branch`
- [x] wizard.py — deleted `branch_workflow_prompt()`, `cmd_branch_workflow_prompt()`, and the `"branch-workflow-prompt"` dispatcher entry
- [x] .squidsquad/config.md — deleted `## Branch Workflow` section (CONTEXT D1)
- [x] All 7 scripts import cleanly after edits

## Slice B (next cycle) — sub-skill rewrites + recompose + fixtures

Per CONTEXT §2.2, remove conditional language in:
- references/sub-skills/common/cycle-runner.md
- references/sub-skills/common/git-commit.md
- references/sub-skills/roles/dev/implement-tasks.md
- references/sub-skills/roles/dev/triage-issues.md
- references/sub-skills/roles/dm/delivery-packaging.md
- references/sub-skills/roles/dm/git-commit.md
- references/sub-skills/roles/pm/pipeline-sentinel.md (drop "if branch_workflow" guard around PR conflict detection)
- references/sub-skills/roles/qa/git-commit.md
- references/sub-skills/roles/qa/verification.md

Pattern: locate "If Branch Workflow is enabled, ..." or "When `branch-workflow: yes`, ..."; remove conditional, keep body imperative.

Then per CONTEXT D4:
- `python references/scripts/compose.py deploy {pm,skill,qa,dm}` — regen 4 composed CLAUDE.md
- Copy regenerated output into `tests/comprehension/8697_fixtures/{role}_polling_CLAUDE.md` (and _events_CLAUDE.md if touched)

## Slice C (after Slice B) — docs + test audit + #8812 closure

- SKILL.md L282, L293 — rewrite to describe branch+PR as the only mode
- tests/test_config_functions.py L204 — `test_get_branch_workflow` is now dead, delete
- tests/test_cycle_post.py — several tests reference `branch_workflow` in their config dicts; the `True` cases still work (since branch+PR is now default), the False cases are dead; audit + remove dead branches
- tests/test_comprehension_2195.py — comprehension test about branch workflow enforcement; audit if it depends on the toggle
- PR #8812 — close with supersede comment per CONTEXT D5
- DS review on final diff
- PR open
- Comment "agent reboot deferred to fleet reset per CONTEXT D9"

## Key decisions (locked in CONTEXT)

- D1 — `.squidsquad/config.md` `## Branch Workflow` section deleted as part of the PR (not silent ignore)
- D2 — `branch_workflow` key removed from /status JSON (no external consumers)
- D5 — close PR #8812 as part of #9478 ship
- D7 — hard cutover, single PR
- D8/D9 — agent reboot DEFERRED to fleet reset (after #9725 + #9415 also ship); skill does NOT reboot agents after this PR merges

## Next steps after this cycle

- Slice B (sub-skill rewrites + recompose + fixture regen)
- Slice C (docs + test audit + #8812 closure)
- DS review on final diff
- PR open
- Comment "agent reboot deferred to fleet reset per CONTEXT D9"

## Recently Shipped (this session)

- **#9415** (PR #9738, pending-test/QA) — event ID widening 8→16 hex + nonce per CONTEXT D5
- **#9688** (PR #9737 merged) — orphan claude.exe cleanup per CONTEXT D1-D8
- **#9588** (PR #9726 merged) — lazy-load mode instructions
- **#9665**, **#9398**, **#9481**, **#9562**, **#9574** all shipped earlier this session

## Filed this session (queued)

- **#9739** (PM, medium) — brainstorm: surface degraded-mode events to human (model_router 402, harness down, etc.). Two halves: agent-side reflex fix + visibility design
- **#9725** (skill, high open) — agents read CLAUDE.md but never invoke /loop. Will be #2 in queue after #9478 ships
- **#9724** (skill, low open) — test_run_comprehension* stale mocks
- **#9687** (skill, low open) — cycle_post.py remote-branch race
