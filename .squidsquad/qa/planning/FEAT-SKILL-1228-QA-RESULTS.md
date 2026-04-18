# QA Results — #1228 PM Pipeline Sentinel

## Summary
- Total: 49 (39 TCs + 10 smoke tests)
- Pass: 14
- Fail: 5
- Skip: 30

## Critical Findings

**BLOCKER: The committed state on this branch is inverted.** The single commit (`aab865c`) deleted `pipeline-sentinel.md` and re-added `pr-flow` references to `includes.yml` and PM `CLAUDE.md` template -- the exact opposite of the stated goal. The working tree contains uncommitted fixes that reverse these errors back to a correct state. However:

1. The restored `pipeline-sentinel.md` in the working tree is an **empty file** (0 bytes). The compose system pulls the content from main's existing file (which has the full 50-line sentinel). This means the branch is not actually adding or modifying the sentinel content -- it relies entirely on the pre-existing file from main.
2. The `installer-files.txt` still references `pr-flow.md` (deleted) and does not reference `pipeline-sentinel.md`. This is a pre-existing gap from main but should have been fixed in this issue.
3. Step 6c (Increment Ship Counter) is duplicated in the composed PM CLAUDE.md (once from the testing-and-verification sub-skill, once from the PM template inline text). Pre-existing issue.

**Net effect of the branch (committed + uncommitted):**
- `pr-flow.md` deleted (correct -- consolidation)
- `pipeline-sentinel.md` kept but as 0-byte file (incorrect -- should retain content from main)
- Dev merge instructions added to `common/git-commit.md` (correct)
- Comprehension questions added to `task-intake.md` (correct)
- PM template and includes.yml: uncommitted fixes restore main's state (correct direction but not committed)

## Results

### TC-1: Pipeline sentinel runs every cycle when QA is present
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-2: Pipeline sentinel is skipped during planning suppression
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-3: Sentinel detects stalled pending-ship tickets
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-4: Sentinel nudges dev when pending-ship PR not merged
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-5: Sentinel does not nudge when pending-ship is fresh
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-6: PR conflict detection gated on Branch Workflow (not PR Flow)
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-7: PR conflict detection skipped when Branch Workflow is off
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-8: Sentinel detects CONFLICTING PR and comments on issue
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-9: Dev agent merges own PR at pending-ship
- **Result**: SKIP
- **Evidence**: Requires live dev cycle
- **Notes**: Requires live cycle

### TC-10: Dev handles rebase when merge conflicts exist
- **Result**: SKIP
- **Evidence**: Requires live dev cycle
- **Notes**: Requires live cycle

### TC-11: QA-present gate only skips testing/verification (Steps 3-6)
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-12: PM fallback (no QA) runs full Steps 3-6
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-13: Delivery fallback works when DM absent and QA present
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-14: Post-merge recompose runs when QA is present
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-15: Post-merge recompose silently skips when no references/ changes
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-16: No duplicate merges (dev merges, PM does not also try)
- **Result**: SKIP
- **Evidence**: Requires live PM cycle + dev cycle
- **Notes**: Requires live cycle

### TC-17: Existing auto-merge config respected
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-18: Bug fixes (type:issue) are not auto-merged
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-19: merge:manual label prevents auto-merge
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-20: Multiple pending-ship tasks with conflicting PRs
- **Result**: SKIP
- **Evidence**: Requires live multi-agent scenario
- **Notes**: Requires live cycle

### TC-21: Tasks without PRs (Branch Workflow off)
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-22: PR Flow off but Branch Workflow on (current project config)
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-23: DM present - sentinel does not attempt shipping
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-24: Sentinel step position in Ralph Loop
- **Result**: PASS
- **Evidence**: In the composed PM CLAUDE.md (after `deploy-all`): QA-skip gate at line 319 (inside `testing-and-verification` sub-skill, closes at line 401). Pipeline sentinel at line 529-579 (`<!-- sub-skill: pipeline-sentinel -->` block, Step 6f). Step 7 (Health Check) at line 534. Sentinel is correctly positioned AFTER the QA-skippable block and BEFORE Step 7. It is in a separate sub-skill block, NOT nested inside the QA-skip gate. The sentinel text explicitly states "This step runs every cycle regardless of QA presence."
- **Notes**: Step ordering is: Steps 3-6c (QA-skippable) -> Step 6c (ship counter, dupe) -> Step 6d (delivery fallback) -> Step 6e (post-merge recompose) -> Step 6f (pipeline sentinel) -> Step 7 (health check). Correct.

### TC-25: QA rejects task after dev already merged PR
- **Result**: SKIP
- **Evidence**: Requires live multi-agent scenario
- **Notes**: Requires live cycle

### TC-26: Stalled pending-ship with no open PR
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-27: Sentinel runs with zero pending-ship tasks
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-28: Sentinel with GitHub temporarily unreachable
- **Result**: SKIP
- **Evidence**: Requires live PM cycle with network interruption
- **Notes**: Requires live cycle

### TC-29: QA-absent PM still runs full verification
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-30: Existing auto-merge in delivery-fallback unchanged
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-31: Step 6b PR monitoring unchanged when PR Flow is on
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: TC is partially moot -- pr-flow sub-skill was deleted from this branch. If PR Flow is on and pr-flow.md is absent, Step 6b will not exist in the composed output. This may be intentional (sentinel replaces pr-flow) but creates a regression for PR Flow users.

### TC-32: Ship counter increments correctly
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-33: Planning suppression still works correctly
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-34: Health check (Step 7) runs independently of sentinel
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### TC-35: compose.py deploy-all works, PM CLAUDE.md has sentinel
- **Result**: FAIL
- **Evidence**: `compose.py deploy-all` succeeds (all 4 roles deployed). Composed PM CLAUDE.md contains `<!-- sub-skill: pipeline-sentinel -->` at line 529 with full sentinel content (Step 6f, PR conflict detection, stall detection, PR status sync). However, the test plan requires the QA-skip gate text to say "Skip Steps 3-6 (testing and verification only)" or equivalent narrowed language. The actual text still says "Skip Steps 3-6 entirely" (line 319) -- the gate wording was NOT narrowed.
- **Notes**: The structural separation (sentinel in a separate sub-skill block after the QA-skip block) achieves the correct behavior, but the gate text was supposed to be updated per the test plan expectation. Additionally, the committed code is broken -- uncommitted fixes are required for compose to succeed. The pipeline-sentinel.md file in the working tree is 0 bytes but compose pulls content from the pre-existing main version.

### TC-36: Dev template has merge instruction
- **Result**: PASS
- **Evidence**: Composed `.squidsquad/skill/CLAUDE.md` line 713: `5. **Merge your PR when task reaches pending-ship**: Each cycle, check for your tasks at pending-ship with open PRs:` followed by `tracker.py list-tasks [ROLE] --status pending-ship`, eligibility checks (Auto Merge: yes, type:task, no merge:manual), and `git_ops.py pr-merge`. Source is `references/sub-skills/common/git-commit.md` lines 89-98 (added by this branch).
- **Notes**: Instruction is in the `common/git-commit.md` sub-skill, so all dev roles (skill, etc.) get it. Correctly placed inside the `Branch Workflow: yes` conditional block.

### TC-37: includes.yml has pipeline-sentinel
- **Result**: PASS (with caveat)
- **Evidence**: Working tree `references/roles/pm/includes.yml` line 11: `- pm-specific/pipeline-sentinel`. Positioned after `post-merge-recompose` and before `health-check`.
- **Notes**: CAVEAT: The committed version of includes.yml on this branch has `pr-flow` instead of `pipeline-sentinel`. The working tree has an uncommitted fix that restores the correct state. This must be committed before merge.

### TC-38: Graceful degradation (inspection)
- **Result**: PASS
- **Evidence**: An existing install with the old CLAUDE.md (before #1228) would not have the pipeline-sentinel section. The old template references pr-flow (which exists on main). Old installs would continue to work identically -- pr-flow handles PR monitoring when PR Flow is on, and nothing runs when it's off. No new dependencies or breaking changes. The sentinel is purely additive when deployed via compose.
- **Notes**: Old installs degrade gracefully because they simply lack the sentinel step. No errors, no crashes.

### TC-39: No new config values
- **Result**: PASS
- **Evidence**: `git diff main -- .squidsquad/config.md` shows only a `Shipped Since Last Bump` counter change (3 vs 4), unrelated to #1228. The pipeline-sentinel.md uses existing config values: `Branch Workflow`, `Auto Merge`, `Iteration Interval`. `config.py get branch-workflow` returns `yes`, `config.py get auto-merge` returns `yes`. No new config fields required.
- **Notes**: Stale threshold is derived as 2x Iteration Interval, not a new config field.

## Smoke Tests

### SM-1: pipeline-sentinel.md exists
- **Result**: FAIL
- **Evidence**: File exists at `references/sub-skills/pm-specific/pipeline-sentinel.md` but is **0 bytes** (empty). The compose system pulls the content from the pre-existing main version of the file. On this branch, the commit deleted the file, and it was restored as an empty file in the working tree (untracked).
- **Notes**: Must be restored with full content and committed.

### SM-2: includes.yml references pipeline-sentinel
- **Result**: PASS (uncommitted)
- **Evidence**: Working tree `references/roles/pm/includes.yml` line 11 has `pm-specific/pipeline-sentinel`. Committed version has `pm-specific/pr-flow` instead.
- **Notes**: Uncommitted fix -- must be committed.

### SM-3: compose.py deploy pm completes without errors
- **Result**: PASS
- **Evidence**: `python references/scripts/compose.py deploy-all` output: `pm: 1486 lines -> .squidsquad\pm\CLAUDE.md`. Exit code 0.
- **Notes**: Only works because the working tree fixes are in place. The committed code fails compose (`ERROR: includes.yml for pm references missing sub-skill: pm-specific/pr-flow`).

### SM-4: Composed PM CLAUDE.md contains pipeline sentinel section
- **Result**: PASS
- **Evidence**: Lines 529-579 contain `<!-- sub-skill: pipeline-sentinel -->` block with Step 6f content (PR conflict detection, stall detection, PR status sync).
- **Notes**: Content comes from main's pre-existing pipeline-sentinel.md, not from this branch's empty file.

### SM-5: Composed PM CLAUDE.md QA-skip gate does NOT cover pipeline steps
- **Result**: PASS (structural) / FAIL (textual)
- **Evidence**: Structurally, the pipeline sentinel is in a separate sub-skill block (lines 529-579) outside the testing-and-verification sub-skill (lines 316-401). The QA-skip gate at line 319 is scoped to the testing-and-verification block. Pipeline sentinel is correctly outside. However, the gate text still says "Skip Steps 3-6 entirely" and the sentinel is labeled "Step 6f", creating textual ambiguity. The test plan expected the gate text to be narrowed.
- **Notes**: The structural separation should work for LLM interpretation since the sentinel explicitly says "always runs regardless of QA presence." But the un-narrowed gate text is a gap vs. the test plan expectation.

### SM-6: Dev template mentions merging PRs at pending-ship
- **Result**: PASS
- **Evidence**: `.squidsquad/skill/CLAUDE.md` line 713: "Merge your PR when task reaches pending-ship"
- **Notes**: Correct.

### SM-7: config.py get branch-workflow returns a value
- **Result**: PASS
- **Evidence**: Returns `yes`
- **Notes**: Sentinel dependency satisfied.

### SM-8: config.py get auto-merge returns a value
- **Result**: PASS
- **Evidence**: Returns `yes`
- **Notes**: Sentinel dependency satisfied.

### SM-9: PM cycle with QA present prints sentinel step marker
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

### SM-10: PM cycle with QA absent runs both verification AND sentinel
- **Result**: SKIP
- **Evidence**: Requires live PM cycle
- **Notes**: Requires live cycle

## Cross-Role Consistency

### CR-1: Non-PM roles don't have pipeline-sentinel
- **Result**: PASS
- **Evidence**: `grep pipeline-sentinel .squidsquad/qa/CLAUDE.md` returns no matches. `grep pipeline-sentinel .squidsquad/skill/CLAUDE.md` returns no matches. Only PM includes.yml and PM CLAUDE.md reference pipeline-sentinel.
- **Notes**: Correct -- sentinel is PM-only.

### CR-2: Dev/skill template has merge instructions
- **Result**: PASS
- **Evidence**: `.squidsquad/skill/CLAUDE.md` line 713 has pending-ship merge instructions. Source is `common/git-commit.md` (shared sub-skill).
- **Notes**: All dev roles get this via the common sub-skill.

### CR-3: QA template unchanged
- **Result**: PASS
- **Evidence**: `git diff main -- references/roles/qa/ .squidsquad/qa/CLAUDE.md` returns no changes.
- **Notes**: QA is unaffected by this change.

## Additional Findings

### AF-1: installer-files.txt references deleted pr-flow.md
- **Result**: GAP
- **Evidence**: `references/installer-files.txt` line 102 references `references/sub-skills/pm-specific/pr-flow.md` which was deleted on this branch. `pipeline-sentinel.md` is not listed in installer-files.txt. This is a pre-existing gap from main (where pipeline-sentinel was already in use but not in installer-files.txt), but should have been fixed in this issue.

### AF-2: Step 6c duplicated in composed PM CLAUDE.md
- **Result**: PRE-EXISTING
- **Evidence**: Step 6c appears at lines 398 and 403 -- once from the testing-and-verification sub-skill and once from the PM template inline. Pre-existing issue, not introduced by this branch.

### AF-3: Committed code is inverted
- **Result**: BLOCKER
- **Evidence**: The commit `aab865c` deletes pipeline-sentinel.md and adds pr-flow references -- the opposite of the issue requirements. Working tree fixes exist but are uncommitted. The branch cannot be merged as-is.

### AF-4: pr-flow.md deletion removes PR Flow functionality
- **Result**: OBSERVATION
- **Evidence**: When `PR Flow: yes` is set in config.md, the old Step 6b (pr-flow sub-skill) handled merged/closed PR detection, conflict detection, comment sync, and changes-requested handling. This branch deletes pr-flow.md. The pipeline sentinel covers PR conflict detection and PR status sync, but does NOT cover: comment sync from PR to tracker, or changes-requested review handling. Projects using `PR Flow: yes` will lose this functionality.
- **Notes**: This may be intentional (simplification), but should be explicitly confirmed.

## Verdict

**FAIL** -- The branch cannot be merged in its current state due to:

1. **Committed code is inverted** (AF-3): The commit added pr-flow back and deleted pipeline-sentinel. Uncommitted working tree fixes exist but must be committed.
2. **pipeline-sentinel.md is 0 bytes** (SM-1): The file exists but is empty. Must be restored with the full 50-line content from main.
3. **QA-skip gate text not narrowed** (SM-5/TC-35): Test plan expected "Skip Steps 3-6 (testing and verification only)" but text still says "Skip Steps 3-6 entirely." Structural separation works but creates textual ambiguity.
4. **installer-files.txt not updated** (AF-1): Still references deleted pr-flow.md, missing pipeline-sentinel.md.

Items 1-2 are blockers. Items 3-4 are gaps that should be fixed before shipping.
